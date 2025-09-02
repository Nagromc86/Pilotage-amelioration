
# CHAP1 v21 – Export Excel CR formatés (tableaux)

Cette mise à jour ajoute un export Excel prêt à copier-coller dans Word/PowerPoint :
- 1 feuille **Index** (liens vers chaque réunion)
- 1 feuille **par réunion**, avec un tableau **Élément / Valeur** :
  Date, Thématique, Projet, Participants, Synthèse, Actions (liste avec puces).

## Installation (sur votre dépôt)
1. Copiez le fichier `optimisation_pilotage/modules/export_fmt.py` dans votre repo.
2. Modifiez `optimisation_pilotage/app.py` selon `docs/APP_MOD.patch.txt` :
   - Ajout d'un bouton dans l'onglet **Export**
   - Ajout de la méthode `_do_export_formatted_tables`
3. (Option) Remplacez votre workflow GitHub Actions par `.github/workflows/main.yml` pour générer `CHAP1_v21.exe`.

## Utilisation
- Onglet **Export** → bouton **Export : Excel (CR formatés — tableaux)**
- Le fichier sera créé dans votre dossier `exports` avec un nom `CR_formates_tableaux_YYYYMMDD_HHMMSS.xlsx`
