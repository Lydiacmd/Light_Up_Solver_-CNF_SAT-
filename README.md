## 🎮 Description


<!-- Failed to upload "Enregistrement de l'écran 2025-11-08 150203.mp4" -->

**Light Up** (ou **Akari**) est un jeu de logique sur une grille rectangulaire composée de cases blanches et de cases noires. Certaines cases noires comportent un chiffre (de 0 à 4) qui indique combien d'ampoules doivent leur être adjacentes.

### 🎯 But du jeu

Placer des ampoules sur certaines cases blanches de manière à ce que :

1.  **Toutes les cases blanches soient éclairées**
2.  **Une ampoule éclaire en ligne droite** (horizontalement et verticalement) jusqu'à rencontrer une case noire ou le bord de la grille
3.  **Deux ampoules ne doivent jamais s'éclairer mutuellement**
4. **Les cases noires numérotées doivent avoir exactement le bon nombre d'ampoules adjacentes**

### Exemple visuel

```
Grille initiale           Solution
. . #1 . .               * A * . .
. # . . #2               * # * A *
#3 . . # .               A * * # A
. . # . .                * * # A *
. #0 . . .               * # . * *

Légende :
  .  = Case blanche
  #  = Mur noir
  #N = Mur avec contrainte (N ampoules adjacentes requises)
  A  = Ampoule placée
  *  = Case éclairée
```

---

## 🚀 Utilisation

### 1️⃣ Générer une grille

```bash
# Grille solvable (normale)
python3 genere_grille.py moyen 7 7

# Grille impossible (unsolvable)
python3 genere_grille.py difficile 8 8 -unsolvable
```

**Paramètres :**
- **Difficulté** : `facile`, `moyen`, `difficile`
- **Dimensions** : `hauteur largeur`
- **Option** : `-unsolvable` (force génération sans solution)

**Sortie :** `grille_light_up.txt`

### 2️⃣ Résoudre en ligne de commande

```bash
python3 dimacs.py grille_light_up.txt
```
`dimacs.py` - Solveur SAT principal
**Flux d'exécution :**

```
┌─────────────────────┐
│  Grille Light Up    │
│  (fichier .txt)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Création variables │
│  (1 par case .)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Génération clauses │
│  - Éclairage (C1)   │
│  - Alignement (C2)  │
│  - Murs #N (C3)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Fichier DIMACS     │
│  output.cnf         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     MiniSAT         │
│  (subprocess)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Solution ou UNSAT  │
│  solution.txt       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Grille résolue +   │
│  vérification       │
└─────────────────────┘
```


### 3️⃣ Interface graphique

```bash
python3 graphe_lightup.py grille_light_up.txt
```

**Fonctionnalités :**
-  **Mode manuel** : Cliquer pour placer/retirer des ampoules
-  **Solution SAT** : Résolution automatique
-  **Vérification** : Valider une solution manuelle
-  **Regles** : Rappele les regles du jeu

---
## 📦 Installation

### Prérequis

**Linux/Ubuntu :**
```bash
sudo apt-get update
sudo apt-get install python3 python3-tk minisat
```

**macOS :**
```bash
brew install python python-tk minisat
```

**Windows :**
1. Télécharge Python depuis [python.org](https://www.python.org/downloads/)
2. Télécharge MiniSAT depuis [minisat.se](http://minisat.se/downloads.html)
3. Place `minisat.exe` dans le dossier du projet


<p align="center">
  Made with ❤️ and ☕ at UGA
</p>



