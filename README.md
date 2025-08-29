# Optimisation_Pilotage — Cloud Build sécurisé (v2)

- Workflow Windows **PowerShell-safe** (smoke test corrigé, pas de `<<'PY'`).
- Clean build, smoke test d'import, build PyInstaller **sans** `--add-data "data;data"`.

## Étapes
1) Uploade **le contenu** du ZIP dans ton repo GitHub.
2) Actions → **Build Windows EXE (secure v2)** → Run workflow.
3) Artefact **Optimisation_Pilotage_exe** → `Optimisation_Pilotage.exe`.
