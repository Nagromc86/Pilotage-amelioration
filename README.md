# CHAP1 — v12 (EXE autonome)

- EXE autonome **CHAP1_v12.exe** (pas de Python local nécessaire).
- Export Excel: 3 feuilles (CR, ToDo, ToDo_Global avec Date réunion, Thématique/Projet, Action, Acteur, Échéance, Statut, IDs, Créé).
- Audio fichiers: WAV uniquement. Live: mix micro + système.
- Données: `%LOCALAPPDATA%/Optimisation_Pilotage/data/` (exports dans `.../exports`).

## Build
Pousse ce dossier à la **racine** du repo puis lance l’action **Build Windows EXE (CHAP1_v12)** (fournie dans `.github/workflows/build_v12.yml`). Récupère l’artefact **CHAP1_v12_exe** → `CHAP1_v12.exe`.

## Offline (optionnel)
Place un modèle CTranslate2 dans `%LOCALAPPDATA%/Optimisation_Pilotage/data/models/faster-whisper-small` (ou `...-medium`) pour éviter tout téléchargement au premier usage.
