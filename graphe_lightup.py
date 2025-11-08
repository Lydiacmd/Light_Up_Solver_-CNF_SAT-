import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import random
import tempfile
import subprocess
from itertools import combinations

# Couleurs
COULEUR_FOND = "#F0F0F0"
COULEUR_CASE_VIDE = "#FFFFFF"
COULEUR_MUR = "#4A4A4A"
COULEUR_MUR_CHIFFRE = "#303030"
COULEUR_AMPOULE = "#FFD700"
COULEUR_ECLAIREE = "#FFFACD"
COULEUR_ERREUR = "#FF6347"
COULEUR_TEXTE_MUR = "#FFFFFF"

# ===== FONCTIONS DU SOLVEUR SAT =====

def est_dans_grille(i, j, H, L):
    """Vérifie si les coordonnées sont dans la grille"""
    return 0 <= i < H and 0 <= j < L

def voisins(i, j, H, L):
    """Retourne les coordonnées des cases voisines"""
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    return [(i+di, j+dj) for di, dj in dirs if est_dans_grille(i+di, j+dj, H, L)]

def case_est_blanche(cellule):
    """Vérifie si la cellule est une case blanche"""
    return cellule == '.'

def mur_chiffre(cellule):
    """Vérifie si la cellule est un mur avec un chiffre"""
    return isinstance(cellule, str) and cellule.startswith('#') and len(cellule) > 1

def generer_dimacs(grille):
    """Génère le problème SAT au format DIMACS"""
    H = len(grille)
    L = len(grille[0])
    clauses = []
    var_map = {}
    var_id = 1

    # Création d'une variable pour chaque case blanche
    for i in range(H):
        for j in range(L):
            if case_est_blanche(grille[i][j]):
                var_map[(i, j)] = var_id
                var_id += 1

    # Pour chaque paire de cases blanches alignées sans mur entre elles,
    # interdire d'avoir des ampoules sur les deux cases
    for (i, j), v1 in var_map.items():
        for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
            ni, nj = i+di, j+dj
            while est_dans_grille(ni, nj, H, L):
                if not case_est_blanche(grille[ni][nj]):
                    break  # On s'arrête aux murs
                v2 = var_map[(ni, nj)]
                clauses.append([-v1, -v2])
                ni += di
                nj += dj

    # Chaque case blanche doit être éclairée par au moins une ampoule
    # (soit elle contient une ampoule, soit une ampoule l'éclaire)
    for (i, j), v in var_map.items():
        sources = [v]  # L'ampoule peut être sur cette case
        for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
            ni, nj = i+di, j+dj
            while est_dans_grille(ni, nj, H, L):
                if not case_est_blanche(grille[ni][nj]):
                    break  # On s'arrête aux murs
                sources.append(var_map[(ni, nj)])  # Ou une ampoule depuis cette direction
                ni += di
                nj += dj
        clauses.append(sources)

    # Pour chaque mur avec un chiffre, exactement N cases adjacentes doivent avoir une ampoule
    for i in range(H):
        for j in range(L):
            if mur_chiffre(grille[i][j]):
                chiffre = int(grille[i][j][1:])
                # Ne considérer que les cases blanches adjacentes
                cases_voisines = [(ni,nj) for ni,nj in voisins(i,j,H,L) if (ni,nj) in var_map]
                vars_voisins = [var_map[pos] for pos in cases_voisines]
                
                if chiffre > len(vars_voisins):
                    messagebox.showerror("Erreur", f"Mur #{chiffre} en ({i},{j}) nécessite {chiffre} voisins mais seulement {len(vars_voisins)} disponibles")
                    return None, None

                # Pour implémenter "exactement N ampoules", nous avons besoin de:
                # 1. "Au moins N ampoules" ET
                # 2. "Au plus N ampoules"

                # 1. Au moins 'chiffre' ampoules
                if chiffre > 0:
                    # Toutes les combinaisons de (len(vars_voisins) - chiffre + 1) variables ne peuvent pas être toutes fausses
                    for comb in combinations(vars_voisins, len(vars_voisins) - chiffre + 1):
                        # Pour chaque combinaison, au moins une variable doit être vraie
                        clause = list(comb)
                        clauses.append(clause)

                # 2. Au plus 'chiffre' ampoules
                if chiffre < len(vars_voisins):
                    # Toutes les combinaisons de (chiffre + 1) variables ne peuvent pas être toutes vraies
                    for comb in combinations(vars_voisins, chiffre + 1):
                        # Pour chaque combinaison, au moins une variable doit être fausse
                        clause = [-v for v in comb]
                        clauses.append(clause)

                # Si chiffre est 0, on ajoute une clause pour chaque variable
                # indiquant qu'elle doit être fausse
                if chiffre == 0:
                    for v in vars_voisins:
                        clauses.append([-v])

    # Création du fichier DIMACS
    fd, nom_fichier = tempfile.mkstemp(suffix='.cnf')
    os.close(fd)
    
    nb_vars = var_id - 1
    nb_clauses = len(clauses)

    with open(nom_fichier, 'w') as f:
        f.write(f"p cnf {nb_vars} {nb_clauses}\n")
        for clause in clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")

    return var_map, nom_fichier

def appeler_sat_solver(nom_fichier):
    """Appelle un solveur SAT externe (MiniSAT par défaut) et retourne le résultat"""
    try:
        out_file = tempfile.mktemp(suffix='.out')
        
        # Vérifiez que MiniSAT est installé
        result = subprocess.run(["minisat", nom_fichier, out_file], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, check=False)
        
        # Vérifiez si le problème est satisfiable
        if "UNSATISFIABLE" in result.stdout or "UNSAT" in result.stderr:
            return None
            
        # Lire la solution
        with open(out_file, "r") as f:
            lines = f.readlines()
            if len(lines) > 0:
                if lines[0].strip() == "SAT":
                    if len(lines) > 1:
                        solution = lines[1].strip().split()
                        return [int(x) for x in solution if x != "0"]
                    else:
                        return []
                else:
                    return None
            else:
                return None
    except FileNotFoundError:
        messagebox.showerror("Erreur", "MiniSAT n'est pas installé ou n'est pas dans le PATH.")
        return None
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de l'appel du solveur SAT: {e}")
        return None
    finally:
        # Nettoyer les fichiers temporaires
        try:
            if os.path.exists(nom_fichier):
                os.remove(nom_fichier)
            if os.path.exists(out_file):
                os.remove(out_file)
        except:
            pass

def interpreter_solution(solution, grille, var_map):
    """Interprète la solution du solveur SAT et renvoie une nouvelle grille avec la solution"""
    if solution is None:
        return None
    
    # Créer une carte inverse: variable -> coordonnées
    coord_map = {v: k for k, v in var_map.items()}
        
    H = len(grille)
    L = len(grille[0])
    
    # Créer une nouvelle grille pour la solution
    solution_grille = []
    for i in range(H):
        ligne = []
        for j in range(L):
            if grille[i][j] == '.':
                ligne.append('.')  # Case blanche vide
            else:
                ligne.append(grille[i][j])  # Mur ou mur chiffré
        solution_grille.append(ligne)
    
    # Placer les ampoules selon la solution
    for var in solution:
        if var > 0:  # Variable positive = ampoule
            if var in coord_map:
                i, j = coord_map[var]
                solution_grille[i][j] = 'A'  # 'A' pour ampoule
    
    return solution_grille

# ===== INTERFACE GRAPHIQUE =====

class LightUpGUI:
    def __init__(self, root, fichier_grille=None):
        self.root = root
        self.root.title("Light Up Puzzle")
        self.root.configure(bg=COULEUR_FOND)
        
        # Variables
        self.grille = []
        self.solution = []
        self.taille_cellule = 50
        self.marge = 20
        self.mode_edition = False
        self.outil_actuel = "mur"  # Options: "mur", "mur_chiffre", "vide", "ampoule"
        
        # Cadre principal
        self.frame_principal = tk.Frame(root, bg=COULEUR_FOND)
        self.frame_principal.pack(padx=10, pady=10)
        
        # Canvas pour dessiner la grille
        self.canvas = tk.Canvas(self.frame_principal, bg=COULEUR_FOND, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Panneau de contrôle
        self.panneau_controle = tk.Frame(self.frame_principal, bg=COULEUR_FOND)
        self.panneau_controle.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.Y)
        
        self.creer_menu()
        self.creer_panneau_controle()
        
        # Initialisation avec une grille vide 5x5 ou chargement d'un fichier
        if fichier_grille and os.path.exists(fichier_grille):
            self.charger_grille_depuis_fichier(fichier_grille)
        else:
            self.initialiser_grille(5, 5)
        
    def creer_menu(self):
        """Crée la barre de menu"""
        menubar = tk.Menu(self.root)
        
        # Menu Fichier
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Nouvelle grille", command=self.nouvelle_grille)
        filemenu.add_command(label="Ouvrir", command=self.ouvrir_grille)
        filemenu.add_command(label="Sauvegarder", command=self.sauvegarder_grille)
        filemenu.add_separator()
        filemenu.add_command(label="Quitter", command=self.root.quit)
        menubar.add_cascade(label="Fichier", menu=filemenu)
        
        # Menu Mode
        modemenu = tk.Menu(menubar, tearoff=0)
        modemenu.add_command(label="Mode Jeu", command=lambda: self.changer_mode(False))
        modemenu.add_command(label="Mode Édition", command=lambda: self.changer_mode(True))
        menubar.add_cascade(label="Mode", menu=modemenu)
        
        # Menu Grille aléatoire
        randommenu = tk.Menu(menubar, tearoff=0)
        randommenu.add_command(label="Facile (5x5)", command=lambda: self.generer_grille_aleatoire(5, 5, 0.1))
        randommenu.add_command(label="Moyenne (7x7)", command=lambda: self.generer_grille_aleatoire(7, 7, 0.3))
        randommenu.add_command(label="Difficile (10x10)", command=lambda: self.generer_grille_aleatoire(10, 10, 0.5))
        menubar.add_cascade(label="Générer", menu=randommenu)
        
        # Menu SAT
        satmenu = tk.Menu(menubar, tearoff=0)
        satmenu.add_command(label="Résoudre avec SAT", command=self.resoudre_avec_sat)
        satmenu.add_command(label="Vérifier validité SAT", command=self.verifier_validite_sat)
        menubar.add_cascade(label="Solveur SAT", menu=satmenu)
        
        # Menu Aide
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Règles", command=self.afficher_regles)
        helpmenu.add_command(label="À propos", command=self.afficher_a_propos)
        menubar.add_cascade(label="Aide", menu=helpmenu)
        
        self.root.config(menu=menubar)
    
    def creer_panneau_controle(self):
        """Crée le panneau de contrôle"""
        # Titre
        tk.Label(self.panneau_controle, text="Contrôles", font=("Arial", 14, "bold"), bg=COULEUR_FOND).pack(pady=(0, 10))
        
        # Boutons de jeu
        frame_boutons_jeu = tk.Frame(self.panneau_controle, bg=COULEUR_FOND)
        frame_boutons_jeu.pack(pady=5, fill=tk.X)
        
        tk.Button(frame_boutons_jeu, text="Vérification", command=self.verifier_solution, width=12).pack(pady=2)
        # Remplacer "Indice" par "Règles"
        tk.Button(frame_boutons_jeu, text="Règles", command=self.afficher_regles, width=12).pack(pady=2)
        tk.Button(frame_boutons_jeu, text="Solution SAT", command=self.resoudre_avec_sat, width=12).pack(pady=2)
        tk.Button(frame_boutons_jeu, text="Réinitialiser", command=self.reinitialiser_grille, width=12).pack(pady=2)
        
        # Séparateur
        tk.Frame(self.panneau_controle, height=2, bg="#AAAAAA").pack(fill=tk.X, pady=10)
        
        # Outils d'édition (initialement cachés)
        self.frame_edition = tk.Frame(self.panneau_controle, bg=COULEUR_FOND)
        
        tk.Label(self.frame_edition, text="Outils d'édition", font=("Arial", 12, "bold"), bg=COULEUR_FOND).pack(pady=(0, 5))
        
        # Variable pour le bouton radio
        self.var_outil = tk.StringVar()
        self.var_outil.set("mur")
        
        # Boutons radio pour les outils
        outils = [
            ("Mur", "mur"),
            ("Mur chiffré", "mur_chiffre"),
            ("Case vide", "vide"),
            ("Ampoule", "ampoule")
        ]
        
        for text, value in outils:
            tk.Radiobutton(self.frame_edition, text=text, variable=self.var_outil, 
                         value=value, bg=COULEUR_FOND, command=self.changer_outil).pack(anchor=tk.W)
        
        # Entrée pour le chiffre du mur
        frame_chiffre = tk.Frame(self.frame_edition, bg=COULEUR_FOND)
        frame_chiffre.pack(pady=5, fill=tk.X)
        
        tk.Label(frame_chiffre, text="Chiffre:", bg=COULEUR_FOND).pack(side=tk.LEFT)
        self.entree_chiffre = tk.Spinbox(frame_chiffre, from_=0, to=4, width=3)
        self.entree_chiffre.pack(side=tk.LEFT, padx=5)
        
        # Bouton pour effacer la grille
        tk.Button(self.frame_edition, text="Effacer la grille", command=self.effacer_grille).pack(pady=(10, 0))
    
    def initialiser_grille(self, hauteur, largeur):
        """Initialise une grille vide avec les dimensions spécifiées"""
        self.grille = [['.' for _ in range(largeur)] for _ in range(hauteur)]
        self.solution = [['.' for _ in range(largeur)] for _ in range(hauteur)]
        self.redessiner_grille()
    
    def redessiner_grille(self):
        """Redessine la grille complète"""
        self.canvas.delete("all")
        
        hauteur = len(self.grille)
        largeur = len(self.grille[0])
        
        # Ajuster la taille de la fenêtre selon la taille de la grille
        taille_max = 800  # Taille maximale pour le canvas
        self.taille_cellule = min(50, (taille_max - 2*self.marge) // max(hauteur, largeur))
        
        # Définir la taille du canvas
        largeur_canvas = largeur * self.taille_cellule + 2 * self.marge
        hauteur_canvas = hauteur * self.taille_cellule + 2 * self.marge
        self.canvas.config(width=largeur_canvas, height=hauteur_canvas)
        
        # Dessiner chaque cellule
        for i in range(hauteur):
            for j in range(largeur):
                x1 = j * self.taille_cellule + self.marge
                y1 = i * self.taille_cellule + self.marge
                x2 = x1 + self.taille_cellule
                y2 = y1 + self.taille_cellule
                
                cellule = self.grille[i][j]
                
                # Déterminer la couleur de la cellule
                if cellule == '.':
                    couleur = COULEUR_CASE_VIDE
                elif cellule == '#':
                    couleur = COULEUR_MUR
                elif isinstance(cellule, str) and cellule.startswith('#') and len(cellule) > 1:
                    couleur = COULEUR_MUR_CHIFFRE
                elif cellule == 'A':
                    couleur = COULEUR_AMPOULE
                elif cellule == '*':
                    couleur = COULEUR_ECLAIREE
                else:
                    couleur = COULEUR_CASE_VIDE
                
                # Dessiner le rectangle
                id_rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=couleur, outline="#AAAAAA")
                
                # Ajouter un texte si c'est un mur chiffré
                if isinstance(cellule, str) and cellule.startswith('#') and len(cellule) > 1:
                    chiffre = cellule[1:]
                    self.canvas.create_text((x1+x2)//2, (y1+y2)//2, text=chiffre, 
                                          fill=COULEUR_TEXTE_MUR, font=("Arial", int(self.taille_cellule * 0.5)))
                
                # Dessiner une ampoule
                elif cellule == 'A':
                    centre_x = (x1 + x2) // 2
                    centre_y = (y1 + y2) // 2
                    rayon = int(self.taille_cellule * 0.35)
                    self.canvas.create_oval(centre_x - rayon, centre_y - rayon,
                                          centre_x + rayon, centre_y + rayon,
                                          fill=COULEUR_AMPOULE, outline="#B8860B")
                    
                    # Ajouter des rayons
                    for angle in range(0, 360, 45):
                        angle_rad = angle * 3.14159 / 180
                        dx = rayon * 0.7 * (angle % 90 == 0 and 1 or 0.7) * (angle < 180 and 1 or -1) * (angle % 270 != 0 and 1 or -1)
                        dy = rayon * 0.7 * (angle % 90 != 0 and 1 or 0.7) * (angle < 270 and angle > 90 and 1 or -1)
                        self.canvas.create_line(centre_x, centre_y, centre_x + dx, centre_y + dy, 
                                              fill="#FFB90F", width=2)
                
                # Ajouter les coordonnées comme balise pour l'interaction
                self.canvas.tag_bind(id_rect, "<Button-1>", lambda event, i=i, j=j: self.clic_case(i, j))
    
    def changer_mode(self, mode_edition):
        """Change entre le mode jeu et le mode édition"""
        self.mode_edition = mode_edition
        if mode_edition:
            self.frame_edition.pack(fill=tk.X, pady=5)
            messagebox.showinfo("Mode Édition", "Vous êtes maintenant en mode édition. Vous pouvez modifier la grille.")
        else:
            self.frame_edition.pack_forget()
            self.reinitialiser_grille()
            messagebox.showinfo("Mode Jeu", "Vous êtes maintenant en mode jeu. Placez des ampoules pour éclairer toute la grille.")
    
    def changer_outil(self):
        """Change l'outil sélectionné"""
        self.outil_actuel = self.var_outil.get()
    
    def clic_case(self, i, j):
        """Gère le clic sur une case de la grille"""
        if self.mode_edition:
            self.modifier_case(i, j)
        else:
            self.placer_ampoule(i, j)
        
        # Redessiner la grille
        self.redessiner_grille()
    
    def modifier_case(self, i, j):
        """Modifie une case en mode édition"""
        if self.outil_actuel == "mur":
            self.grille[i][j] = '#'
        elif self.outil_actuel == "mur_chiffre":
            chiffre = self.entree_chiffre.get()
            self.grille[i][j] = f'#{chiffre}'
        elif self.outil_actuel == "vide":
            self.grille[i][j] = '.'
        elif self.outil_actuel == "ampoule":
            self.grille[i][j] = 'A'
    
    def placer_ampoule(self, i, j):
        """Place ou retire une ampoule en mode jeu"""
        # Vérifier si la case est valide pour placer une ampoule
        if self.grille[i][j] in ['.', '*', 'A']:
            # Si déjà une ampoule, la retirer
            if self.grille[i][j] == 'A':
                self.grille[i][j] = '.'
            else:
                self.grille[i][j] = 'A'
            
            # Mettre à jour l'éclairage
            self.mettre_a_jour_eclairage()
    
    def mettre_a_jour_eclairage(self):
        """Met à jour l'éclairage des cases après placement d'ampoules"""
        hauteur = len(self.grille)
        largeur = len(self.grille[0])
        
        # Réinitialiser les cases éclairées
        for i in range(hauteur):
            for j in range(largeur):
                if self.grille[i][j] == '*':
                    self.grille[i][j] = '.'
        
        # Marquer les cases éclairées par chaque ampoule
        for i in range(hauteur):
            for j in range(largeur):
                if self.grille[i][j] == 'A':
                    # Éclairer dans les 4 directions
                    for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ni, nj = i + di, j + dj
                        while 0 <= ni < hauteur and 0 <= nj < largeur:
                            # S'arrêter aux murs
                            if self.grille[ni][nj] == '#' or (isinstance(self.grille[ni][nj], str) and self.grille[ni][nj].startswith('#')):
                                break
                            # Marquer comme éclairé si ce n'est pas une ampoule
                            if self.grille[ni][nj] != 'A':
                                self.grille[ni][nj] = '*'
                            ni += di
                            nj += dj
    
    def nouvelle_grille(self):
        """Crée une nouvelle grille"""
        hauteur = simpledialog.askinteger("Nouvelle grille", "Hauteur de la grille:", minvalue=3, maxvalue=20)
        if hauteur is None:
            return
        
        largeur = simpledialog.askinteger("Nouvelle grille", "Largeur de la grille:", minvalue=3, maxvalue=20)
        if largeur is None:
            return
        
        self.initialiser_grille(hauteur, largeur)
    
    def ouvrir_grille(self):
        """Ouvre une grille à partir d'un fichier"""
        fichier = filedialog.askopenfilename(filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")])
        if not fichier:
            return
        
        self.charger_grille_depuis_fichier(fichier)
    
    def charger_grille_depuis_fichier(self, fichier):
        """Charge une grille depuis un fichier spécifié"""
        try:
            with open(fichier, 'r') as f:
                lignes = [ligne.strip().split() for ligne in f.readlines()]
            
            # Vérifier que la grille est valide
            if not lignes or not lignes[0]:
                raise ValueError("Grille vide ou invalide")
            
            self.grille = lignes
            
            self.redessiner_grille()
            messagebox.showinfo("Succès", f"Grille chargée depuis {os.path.basename(fichier)}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lire le fichier: {e}")
    
    def sauvegarder_grille(self):
        """Sauvegarde la grille dans un fichier"""
        fichier = filedialog.asksaveasfilename(defaultextension=".txt",
                                              filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")])
        if not fichier:
            return
        
        try:
            with open(fichier, 'w') as f:
                for ligne in self.grille:
                    f.write(" ".join(str(cellule) for cellule in ligne) + "\n")
            messagebox.showinfo("Succès", f"Grille sauvegardée dans {os.path.basename(fichier)}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de sauvegarder le fichier: {e}")
    
    def verifier_solution(self):
        """Vérifie si la solution actuelle est valide"""
        # Vérifier que toutes les cases blanches sont éclairées
        hauteur = len(self.grille)
        largeur = len(self.grille[0])
        
        # Vérifier que toutes les cases blanches sont éclairées
        for i in range(hauteur):
            for j in range(largeur):
                if self.grille[i][j] == '.':  # Case blanche non éclairée
                    messagebox.showinfo("Vérification", "Il y a encore des cases non éclairées.")
                    return False
        
        # Vérifier que les ampoules ne s'éclairent pas entre elles
        for i in range(hauteur):
            for j in range(largeur):
                if self.grille[i][j] == 'A':
                    # Vérifier dans les 4 directions
                    for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ni, nj = i + di, j + dj
                        while 0 <= ni < hauteur and 0 <= nj < largeur:
                            # S'arrêter aux murs
                            if self.grille[ni][nj] == '#' or (isinstance(self.grille[ni][nj], str) and self.grille[ni][nj].startswith('#')):
                                break
                            if self.grille[ni][nj] == 'A':  # Une autre ampoule est visible
                                messagebox.showinfo("Vérification", f"Les ampoules en ({i},{j}) et ({ni},{nj}) s'éclairent mutuellement.")
                                return False
                            ni += di
                            nj += dj
        
        # Vérifier les contraintes de murs chiffrés
        for i in range(hauteur):
            for j in range(largeur):
                if isinstance(self.grille[i][j], str) and self.grille[i][j].startswith('#') and len(self.grille[i][j]) > 1:
                    chiffre = int(self.grille[i][j][1:])
                    voisins_coords = [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]
                    ampoules_adjacentes = sum(1 for ni, nj in voisins_coords 
                                          if 0 <= ni < hauteur and 0 <= nj < largeur and self.grille[ni][nj] == 'A')
                    if ampoules_adjacentes != chiffre:
                        messagebox.showinfo("Vérification", f"Le mur en ({i},{j}) doit avoir exactement {chiffre} ampoules adjacentes.")
                        return False
        
        messagebox.showinfo("Félicitations", "Votre solution est correcte!")
        return True
    
    def resoudre_avec_sat(self):
        """Résout la grille en utilisant le solveur SAT"""
        # Afficher un message d'attente
        self.root.config(cursor="watch")
        self.root.update()
        
        try:
            # Générer le problème SAT
            var_map, nom_fichier = generer_dimacs(self.grille)
            
            if var_map is None:
                messagebox.showerror("Erreur", "Impossible de générer le problème SAT.")
                return
            
            # Appeler le solveur SAT
            solution = appeler_sat_solver(nom_fichier)
            
            if solution is None:
                messagebox.showinfo("Résultat", "Aucune solution n'a été trouvée. La grille est peut-être invalide.")
                return
            
            # Interpréter la solution
            solution_grille = interpreter_solution(solution, self.grille, var_map)
            
            if solution_grille is None:
                messagebox.showerror("Erreur", "Erreur dans l'interprétation de la solution.")
                return
            
            # Afficher la solution
            self.grille = solution_grille
            self.mettre_a_jour_eclairage()
            self.redessiner_grille()
            messagebox.showinfo("Succès", "Solution trouvée avec le solveur SAT!")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la résolution SAT: {e}")
        finally:
            self.root.config(cursor="")
    
    def verifier_validite_sat(self):
        """Vérifie si la grille a une solution valide avec le solveur SAT"""
        # Afficher un message d'attente
        self.root.config(cursor="watch")
        self.root.update()
        
        try:
            # Générer le problème SAT
            var_map, nom_fichier = generer_dimacs(self.grille)
            
            if var_map is None:
                messagebox.showerror("Erreur", "Impossible de générer le problème SAT.")
                return
            
            # Appeler le solveur SAT
            solution = appeler_sat_solver(nom_fichier)
            
            if solution is None:
                messagebox.showinfo("Résultat", "La grille n'a pas de solution valide.")
            else:
                messagebox.showinfo("Résultat", "La grille a au moins une solution valide.")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la vérification SAT: {e}")
        finally:
            self.root.config(cursor="")
    
    def afficher_regles(self):
        """Affiche les règles du jeu"""
        regles = """
Règles du jeu Light Up:

1. Le but est d'éclairer toutes les cases blanches en plaçant des ampoules.
2. Les ampoules éclairent horizontalement et verticalement jusqu'à un mur.
3. Les ampoules ne peuvent pas s'éclairer mutuellement.
4. Les murs avec un chiffre indiquent exactement combien d'ampoules doivent être placées dans les cases adjacentes.

Pour jouer:
- Cliquez sur une case blanche pour y placer ou retirer une ampoule.
- Les cases éclairées sont marquées en jaune clair.
- Utilisez "Vérification" pour voir si votre solution est correcte.
- Utilisez "Solution SAT" pour résoudre automatiquement le puzzle.
        """
        messagebox.showinfo("Règles du jeu", regles)
    
    def afficher_solution(self):
        """Affiche la solution du puzzle (utilise le solveur SAT)"""
        self.resoudre_avec_sat()
    
    def reinitialiser_grille(self):
        """Réinitialise la grille en enlevant toutes les ampoules et cases éclairées"""
        hauteur = len(self.grille)
        largeur = len(self.grille[0])
        
        for i in range(hauteur):
            for j in range(largeur):
                if self.grille[i][j] in ['A', '*']:
                    self.grille[i][j] = '.'
        
        self.redessiner_grille()
    
    def effacer_grille(self):
        """Efface complètement la grille en mode édition"""
        hauteur = len(self.grille)
        largeur = len(self.grille[0])
        self.grille = [['.' for _ in range(largeur)] for _ in range(hauteur)]
        self.redessiner_grille()
    
    def generer_grille_aleatoire(self, hauteur, largeur, difficulte):
        """Génère une grille aléatoire avec la difficulté spécifiée"""
        # Pour l'instant, on crée juste une grille vide avec quelques murs
        self.initialiser_grille(hauteur, largeur)
        
        # Placer aléatoirement des murs et des murs chiffrés
        nb_murs = int((hauteur * largeur) * (0.3 - difficulte * 0.05))
        murs_places = 0
        
        while murs_places < nb_murs:
            i = random.randint(0, hauteur - 1)
            j = random.randint(0, largeur - 1)
            
            if self.grille[i][j] == '.':
                # 30% de chance d'avoir un mur chiffré
                if random.random() < 0.3:
                    chiffre = random.randint(0, 4)
                    self.grille[i][j] = f'#{chiffre}'
                else:
                    self.grille[i][j] = '#'
                murs_places += 1
        
        self.redessiner_grille()
        
        # Vérifier si la grille générée a une solution
        self.root.config(cursor="watch")
        self.root.update()
        
        try:
            var_map, nom_fichier = generer_dimacs(self.grille)
            if var_map is None:
                messagebox.showinfo("Génération", "La grille générée n'a pas de solution. Essayez à nouveau.")
                return
            
            solution = appeler_sat_solver(nom_fichier)
            if solution is None:
                messagebox.showinfo("Génération", "La grille générée n'a pas de solution. Essayez à nouveau.")
            else:
                messagebox.showinfo("Grille générée", f"Une grille {hauteur}x{largeur} de difficulté {difficulte} a été générée avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la vérification de la grille générée: {e}")
        finally:
            self.root.config(cursor="")
    
    def afficher_a_propos(self):
        """Affiche les informations à propos de l'application"""
        a_propos = """
Light Up Puzzle

Une interface graphique pour jouer au jeu Light Up (Akari).

Cette application utilise un solveur SAT (MiniSAT) pour résoudre automatiquement les puzzles.

Développé avec Python et Tkinter.
        """
        messagebox.showinfo("À propos", a_propos)

def main():
    root = tk.Tk()
    # Récupérer le nom du fichier de grille en argument si disponible
    import sys
    fichier_grille = sys.argv[1] if len(sys.argv) > 1 else None
    app = LightUpGUI(root, fichier_grille)
    root.mainloop()

if __name__ == "__main__":
    main()