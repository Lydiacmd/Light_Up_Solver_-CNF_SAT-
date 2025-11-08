from itertools import combinations

def lire_grille(nom_fichier):
    """Lit une grille à partir d'un fichier"""
    with open(nom_fichier, 'r') as f:
        lignes = [ligne.strip().split() for ligne in f.readlines()]
    return lignes

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
    return cellule.startswith('#') and len(cellule) > 1

def generer_dimacs(grille):
    """Génère le problème SAT au format DIMACS"""
    H = len(grille)
    L = len(grille[0])
    clauses = []
    var_map = {}
    var_id = 1

    print("\n=== PHASE 1: Création des variables ===")
    # Création d'une variable pour chaque case blanche
    for i in range(H):
        for j in range(L):
            if case_est_blanche(grille[i][j]):
                var_map[(i, j)] = var_id
                print(f"Case blanche en ({i},{j}) → variable {var_id}")
                var_id += 1

    print("\n=== PHASE 2: Contraintes d'alignement ===")
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
                print(f"Interdiction ampoules alignées: ({i},{j}) var{v1} et ({ni},{nj}) var{v2}")
                ni += di
                nj += dj

    print("\n=== PHASE 3: Contraintes d'éclairage ===")
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
        print(f"Case ({i},{j}) var{v} doit être éclairée par: {sources}")

    print("\n=== PHASE 4: Contraintes des murs chiffrés ===")
    # Pour chaque mur avec un chiffre, exactement N cases adjacentes doivent avoir une ampoule
    for i in range(H):
        for j in range(L):
            if mur_chiffre(grille[i][j]):
                chiffre = int(grille[i][j][1:])
                # Ne considérer que les cases blanches adjacentes
                cases_voisines = [(ni,nj) for ni,nj in voisins(i,j,H,L) if (ni,nj) in var_map]
                vars_voisins = [var_map[pos] for pos in cases_voisines]
                
                print(f"\nMur #{chiffre} en ({i},{j})")
                print(f"Cases voisines: {cases_voisines}")
                print(f"Variables voisines: {vars_voisins}")

                if chiffre > len(vars_voisins):
                    print(f"ERREUR: Mur #{chiffre} nécessite {chiffre} voisins mais seulement {len(vars_voisins)} disponibles")
                    return None

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
                        print(f"Clause 'au moins {chiffre}': {clause}")

                # 2. Au plus 'chiffre' ampoules
                if chiffre < len(vars_voisins):
                    # Toutes les combinaisons de (chiffre + 1) variables ne peuvent pas être toutes vraies
                    for comb in combinations(vars_voisins, chiffre + 1):
                        # Pour chaque combinaison, au moins une variable doit être fausse
                        clause = [-v for v in comb]
                        clauses.append(clause)
                        print(f"Clause 'au plus {chiffre}': {clause}")

                # Si chiffre est 0, on ajoute une clause pour chaque variable
                # indiquant qu'elle doit être fausse
                if chiffre == 0:
                    for v in vars_voisins:
                        clauses.append([-v])
                        print(f"Clause 'exactement 0': {[-v]}")

    print("\n=== PHASE 5: Génération du fichier DIMACS ===")
    nb_vars = var_id - 1
    nb_clauses = len(clauses)

    with open("output.cnf", "w") as f:
        f.write(f"p cnf {nb_vars} {nb_clauses}\n")
        for clause in clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")

    print(f"Fichier généré: {nb_vars} variables, {nb_clauses} clauses")
    print("Clauses générées:")
    for i, clause in enumerate(clauses, 1):
        print(f"{i}: {clause}")

    return var_map, clauses  # Retourne var_map pour l'utiliser plus tard

def appeler_sat_solver(nom_fichier="output.cnf"):
    """Appelle un solveur SAT externe (MiniSAT par défaut) et retourne le résultat"""
    try:
        import subprocess
        # Vérifiez que MiniSAT est installé
        print("Exécution de MiniSAT avec la commande: minisat", nom_fichier, "solution.txt")
        result = subprocess.run(["minisat", nom_fichier, "solution.txt"], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, check=False)
        
        print("Retour standard de MiniSAT:", result.stdout)
        print("Erreur standard de MiniSAT:", result.stderr)
        
        # Vérifiez si le problème est satisfiable
        if "UNSATISFIABLE" in result.stdout or "UNSAT" in result.stderr:
            print("Le problème n'a pas de solution.")
            return None
            
        # Lire la solution
        print("Lecture du fichier solution.txt")
        with open("solution.txt", "r") as f:
            lines = f.readlines()
            if len(lines) > 0:
                if lines[0].strip() == "SAT":
                    if len(lines) > 1:
                        solution = lines[1].strip().split()
                        variables_vraies = [int(x) for x in solution if int(x) > 0]
                        print(f"Variables vraies dans la solution: {variables_vraies}")
                        return [int(x) for x in solution if x != "0"]
                    else:
                        print("Attention: Fichier solution sans valeurs")
                        return []
                else:
                    print("Format de solution inattendu:", lines)
                    return None
            else:
                print("Fichier solution vide")
                return None
    except FileNotFoundError:
        print("Erreur: MiniSAT n'est pas installé ou n'est pas dans le PATH.")
        print("Veuillez installer MiniSAT (apt-get install minisat) ou un autre solveur SAT compatible.")
        return None
    except Exception as e:
        print(f"Erreur lors de l'appel du solveur SAT: {e}")
        return None

def interpreter_solution(solution, grille, var_map):
    """Interprète la solution du solveur SAT et l'affiche sur la grille"""
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
                ligne.append(' ')  # Case blanche vide
            else:
                ligne.append(grille[i][j])  # Mur ou mur chiffré
        solution_grille.append(ligne)
    
    # Placer les ampoules selon la solution
    for var in solution:
        if var > 0:  # Variable positive = ampoule
            if var in coord_map:
                i, j = coord_map[var]
                solution_grille[i][j] = 'A'  # 'A' pour ampoule
                print(f"Placement d'une ampoule en ({i},{j}) [var{var}]")
            else:
                print(f"ATTENTION: Variable {var} non trouvée dans le mapping")
    
    # Marquer les cases éclairées
    for i in range(H):
        for j in range(L):
            if solution_grille[i][j] == 'A':
                # Marquer la case de l'ampoule comme éclairée
                # Éclairer dans les 4 directions
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ni, nj = i + di, j + dj
                    while est_dans_grille(ni, nj, H, L):
                        # S'arrêter aux murs
                        if solution_grille[ni][nj].startswith('#'):
                            break
                        # Marquer comme éclairé si ce n'est pas une ampoule
                        if solution_grille[ni][nj] != 'A':
                            solution_grille[ni][nj] = '*'
                        ni += di
                        nj += dj
    
    return solution_grille

def afficher_grille(grille):
    """Affiche une grille de façon lisible"""
    for ligne in grille:
        print(" ".join(ligne))

def verifier_solution(solution_grille):
    """Vérifie si la solution est valide"""
    H = len(solution_grille)
    L = len(solution_grille[0])
    
    est_valide = True
    
    # Vérifier que toutes les cases blanches sont éclairées
    for i in range(H):
        for j in range(L):
            if solution_grille[i][j] == ' ':  # Case blanche non éclairée
                print(f"ERREUR: Case ({i},{j}) non éclairée")
                est_valide = False
    
    # Vérifier que les ampoules ne s'éclairent pas entre elles
    for i in range(H):
        for j in range(L):
            if solution_grille[i][j] == 'A':
                # Vérifier dans les 4 directions
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ni, nj = i + di, j + dj
                    while est_dans_grille(ni, nj, H, L):
                        # S'arrêter aux murs
                        if solution_grille[ni][nj].startswith('#'):
                            break
                        if solution_grille[ni][nj] == 'A':  # Une autre ampoule est visible
                            print(f"ERREUR: Ampoules ({i},{j}) et ({ni},{nj}) s'éclairent mutuellement")
                            est_valide = False
                        ni += di
                        nj += dj
    
    # Vérifier les contraintes de murs chiffrés
    for i in range(H):
        for j in range(L):
            if solution_grille[i][j].startswith('#') and len(solution_grille[i][j]) > 1:
                chiffre = int(solution_grille[i][j][1:])
                ampoules_adjacentes = sum(1 for ni, nj in voisins(i, j, H, L) 
                                       if est_dans_grille(ni, nj, H, L) and solution_grille[ni][nj] == 'A')
                if ampoules_adjacentes != chiffre:
                    print(f"ERREUR: Mur ({i},{j}) avec chiffre {chiffre} a {ampoules_adjacentes} ampoules adjacentes")
                    est_valide = False
    
    return est_valide

def afficher_etat_solver(grille, solution=None, var_map=None):
    """Affiche l'état du solveur pour le débogage"""
    H = len(grille)
    L = len(grille[0])
    
    print("=== État actuel du problème ===")
    print("Grille originale:")
    afficher_grille(grille)
    
    if var_map:
        print("\nMapping des variables:")
        for (i, j), var in sorted(var_map.items(), key=lambda x: x[1]):
            print(f"({i},{j}) -> var{var}")
    
    if solution:
        # Créer une carte inverse
        if var_map:
            coord_map = {v: k for k, v in var_map.items()}
            print("\nVariables vraies (ampoules):")
            for var in solution:
                if var > 0 and var in coord_map:
                    i, j = coord_map[var]
                    print(f"var{var} -> ({i},{j})")

def visualiser_contraintes(grille, var_map, clauses):
    """Visualise les contraintes pour chaque case de la grille"""
    H = len(grille)
    L = len(grille[0])
    
    # Créer une carte inverse: variable -> coordonnées
    coord_map = {v: k for k, v in var_map.items()}
    
    # Afficher les contraintes pour chaque variable
    print("\n=== Contraintes par variable ===")
    for var in range(1, max(var_map.values()) + 1):
        if var in coord_map:
            i, j = coord_map[var]
            print(f"\nVariable {var} en ({i},{j}):")
            
            # Trouver toutes les clauses où cette variable apparaît
            var_clauses = []
            for idx, clause in enumerate(clauses):
                if var in clause or -var in clause:
                    var_clauses.append((idx, clause))
            
            print(f"Apparaît dans {len(var_clauses)} clauses:")
            for idx, clause in var_clauses:
                description = "Clause " + str(idx) + ": "
                if var in clause:
                    description += f"Si la case ({i},{j}) n'a PAS d'ampoule, alors "
                else:  # -var in clause
                    description += f"Si la case ({i},{j}) a une ampoule, alors "
                
                autres_vars = [v for v in clause if abs(v) != var]
                if not autres_vars:
                    if var in clause:
                        description += "contradiction (la case DOIT avoir une ampoule)"
                    else:
                        description += "contradiction (la case NE DOIT PAS avoir une ampoule)"
                else:
                    conditions = []
                    for v in autres_vars:
                        if v in coord_map:
                            i2, j2 = coord_map[abs(v)]
                            if v > 0:
                                conditions.append(f"la case ({i2},{j2}) doit avoir une ampoule")
                            else:
                                conditions.append(f"la case ({i2},{j2}) ne doit pas avoir d'ampoule")
                    description += " ou ".join(conditions)
                
                print(description)

def resoudre_light_up(nom_fichier):
    """Fonction principale pour résoudre un puzzle Light Up"""
    print("=== LECTURE DE LA GRILLE ===")
    grille = lire_grille(nom_fichier)
    print("Grille initiale:")
    afficher_grille(grille)
    
    print("\n=== GÉNÉRATION DU PROBLÈME SAT ===")
    var_map, clauses = generer_dimacs(grille)
    
    if var_map is None:
        print("Impossible de générer le problème SAT. La grille est probablement invalide.")
        return
    
    # Visualiser les contraintes pour le débogage
    # visualiser_contraintes(grille, var_map, clauses)
    
    print("\n=== APPEL DU SOLVEUR SAT ===")
    solution = appeler_sat_solver()
    
    if solution is not None:
        print("\n=== SOLUTION TROUVÉE ===")
        print(f"Solution brute de MiniSAT: {solution}")
        afficher_etat_solver(grille, solution, var_map)
        
        solution_grille = interpreter_solution(solution, grille, var_map)
        print("Grille solution:")
        afficher_grille(solution_grille)
        
        print("\n=== VÉRIFICATION DE LA SOLUTION ===")
        if verifier_solution(solution_grille):
            print("La solution est VALIDE !")
        else:
            print("La solution est INVALIDE !")
            
            # Visualiser les contraintes pour voir où ça coince
            visualiser_contraintes(grille, var_map, clauses)
    else:
        print("Aucune solution n'a été trouvée.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        nom_fichier = sys.argv[1]
    else:
        nom_fichier = input("Entrez le nom du fichier de grille: ")
    
    resoudre_light_up(nom_fichier)