import random
import subprocess
import tempfile
import os
from itertools import combinations

def voisins(i, j, n, m):
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    return [(i+di, j+dj) for di, dj in dirs if 0 <= i+di < n and 0 <= j+dj < m]

def mur_chiffre(cellule):
    return cellule.startswith('#') and len(cellule) > 1

def case_est_blanche(cellule):
    return cellule == '.'

def valider_mur_chiffre(grille, i, j, chiffre, n, m):
    cases_blanches_voisines = 0
    for ni, nj in voisins(i, j, n, m):
        cellule_voisine = grille[ni][nj]
        if cellule_voisine == '.':
            cases_blanches_voisines += 1
    
    return chiffre <= cases_blanches_voisines

def generer_dimacs_silent(grille):
    H = len(grille)
    L = len(grille[0])
    clauses = []
    var_map = {}
    var_id = 1

    for i in range(H):
        for j in range(L):
            if case_est_blanche(grille[i][j]):
                var_map[(i, j)] = var_id
                var_id += 1

    for (i, j), v1 in var_map.items():
        for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
            ni, nj = i+di, j+dj
            while 0 <= ni < H and 0 <= nj < L:
                if not case_est_blanche(grille[ni][nj]):
                    break
                v2 = var_map[(ni, nj)]
                clauses.append([-v1, -v2])
                ni += di
                nj += dj

    for (i, j), v in var_map.items():
        sources = [v]
        for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
            ni, nj = i+di, j+dj
            while 0 <= ni < H and 0 <= nj < L:
                if not case_est_blanche(grille[ni][nj]):
                    break
                sources.append(var_map[(ni, nj)])
                ni += di
                nj += dj
        clauses.append(sources)

    for i in range(H):
        for j in range(L):
            if mur_chiffre(grille[i][j]):
                chiffre = int(grille[i][j][1:])
                cases_voisines = [(ni,nj) for ni,nj in voisins(i,j,H,L) if (ni,nj) in var_map]
                vars_voisins = [var_map[pos] for pos in cases_voisines]
                
                if chiffre > len(vars_voisins):
                    return None, None

                if chiffre > 0:
                    for comb in combinations(vars_voisins, len(vars_voisins) - chiffre + 1):
                        clauses.append(list(comb))

                if chiffre < len(vars_voisins):
                    for comb in combinations(vars_voisins, chiffre + 1):
                        clauses.append([-v for v in comb])

                if chiffre == 0:
                    for v in vars_voisins:
                        clauses.append([-v])

    fd, nom_fichier = tempfile.mkstemp(suffix='.cnf')
    os.close(fd)
    
    nb_vars = var_id - 1
    nb_clauses = len(clauses)

    with open(nom_fichier, 'w') as f:
        f.write(f"p cnf {nb_vars} {nb_clauses}\n")
        for clause in clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")

    return var_map, nom_fichier

def tester_grille_avec_sat(grille):
    try:
        var_map, nom_fichier = generer_dimacs_silent(grille)
        
        if var_map is None:
            return False
        
        out_file = tempfile.mktemp(suffix='.out')
        
        result = subprocess.run(["minisat", nom_fichier, out_file], 
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL, 
                              check=False, 
                              timeout=5)
        
        try:
            if os.path.exists(nom_fichier):
                os.remove(nom_fichier)
        except:
            pass
        
        if result.returncode != 10:
            try:
                if os.path.exists(out_file):
                    os.remove(out_file)
            except:
                pass
            return False
            
        try:
            with open(out_file, "r") as f:
                lines = f.readlines()
                if os.path.exists(out_file):
                    os.remove(out_file)
                
                if len(lines) > 0 and lines[0].strip() == "SAT":
                    return True
                else:
                    return False
        except:
            return False
                
    except subprocess.TimeoutExpired:
        return False
    except FileNotFoundError:
        return None
    except Exception as e:
        return False

def generer_grille_light_up(n, m, difficulte='moyen', max_tentatives=1000, forcer_fausse=False):
    niveaux = {
        'facile':    {'p_mur': 0.15, 'p_mur_numerote': 0.40},
        'moyen':     {'p_mur': 0.20, 'p_mur_numerote': 0.50},
        'difficile': {'p_mur': 0.25, 'p_mur_numerote': 0.65},
    }

    if difficulte not in niveaux:
        raise ValueError("Difficulté invalide. Choisir parmi 'facile', 'moyen' ou 'difficile'.")

    p_mur = niveaux[difficulte]['p_mur']
    p_mur_numerote = niveaux[difficulte]['p_mur_numerote']

    if forcer_fausse:
        print(f"Génération d'une grille UNSOLVABLE {n}x{m} de difficulté '{difficulte}'...")
    else:
        print(f"Génération d'une grille {n}x{m} de difficulté '{difficulte}'...")
    print("Cela peut prendre quelques secondes...")
    
    for tentative in range(max_tentatives):
        grille = []
        for i in range(n):
            ligne = []
            for j in range(m):
                r = random.random()
                if r < p_mur:
                    if random.random() < p_mur_numerote:
                        chiffre = random.randint(0, 4)
                        ligne.append(f"#{chiffre}")
                    else:
                        ligne.append('#')
                else:
                    ligne.append('.')
            grille.append(ligne)
        
        grille_valide = True
        for i in range(n):
            for j in range(m):
                if mur_chiffre(grille[i][j]):
                    chiffre = int(grille[i][j][1:])
                    if not valider_mur_chiffre(grille, i, j, chiffre, n, m):
                        grille_valide = False
                        break
            if not grille_valide:
                break
        
        if not grille_valide:
            continue
        
        nb_cases_blanches = sum(1 for ligne in grille for case in ligne if case == '.')
        if nb_cases_blanches < (n * m) * 0.3:
            continue
        
        resultat = tester_grille_avec_sat(grille)
        
        if forcer_fausse:
            if resultat is False:
                print(f"Tentative {tentative + 1}/{max_tentatives}... ✓ Grille UNSOLVABLE générée!")
                return grille
        else:
            if resultat is None:
                print(f"Tentative {tentative + 1}/{max_tentatives}... ✓ Grille valide générée!")
                return grille
            elif resultat:
                print(f"Tentative {tentative + 1}/{max_tentatives}... ✓ Grille valide générée!")
                return grille
    
    if forcer_fausse:
        print(f"\n⚠️  {max_tentatives} tentatives échouées, on continue...")
        return generer_grille_light_up(n, m, difficulte, max_tentatives, forcer_fausse=True)
    else:
        print(f"\n⚠️  {max_tentatives} tentatives échouées, on continue...")
        return generer_grille_light_up(n, m, difficulte, max_tentatives)

def ecrire_grille_dans_fichier(grille, nom_fichier):
    with open(nom_fichier, 'w') as f:
        for ligne in grille:
            f.write(' '.join(ligne) + '\n')
    print(f"\nGrille sauvegardée dans '{nom_fichier}'")

if __name__ == "__main__":
    import sys
    
    hauteur = 7
    largeur = 7
    difficulte = 'moyen'
    forcer_fausse = False
    
    if len(sys.argv) >= 3:
        difficulte = sys.argv[1]
        hauteur = int(sys.argv[2])
        largeur = int(sys.argv[3]) if len(sys.argv) >= 4 else hauteur
        
        if len(sys.argv) >= 5 and sys.argv[4].lower() == '-unsolvable':
            forcer_fausse = True
    
    grille = generer_grille_light_up(hauteur, largeur, difficulte=difficulte, forcer_fausse=forcer_fausse)
    ecrire_grille_dans_fichier(grille, 'grille_light_up.txt')
    
    print("\nGrille générée:")
    for ligne in grille:
        print(' '.join(ligne))