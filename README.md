# CHAP1 — Compte-rendus Harmonisés et Assistance au Pilotage (v9)

## Nouveauté
- **Export Excel** contient **3 feuilles** :
  - **CR** (filtré par Thématique/Projet sélectionnés),
  - **ToDo** (filtré),
  - **ToDo_Global** (**agrège TOUTES** les actions, toutes thématiques/projets), avec colonnes :
    - *Thématique (Domaine), Projet (Sujet), Date réunion, Titre réunion, Action, Acteur, Échéance, Statut, MeetingID, ToDoID, Créé*.

## Rappels
- WAV uniquement (pas d’ffmpeg).
- Fallback micro/HP et chemins utilisateur.
- Modèles Whisper : recherche d’abord en local dans `%LOCALAPPDATA%/Optimisation_Pilotage/data/models/` (small/medium).
- Build via workflow **Build Windows EXE (CHAP1)**.
