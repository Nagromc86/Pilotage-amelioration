# Optimisation_Pilotage — Secure v3 (DB fix)

- **Correction** : la base SQLite est stockée dans un dossier **utilisateur** (Windows: `%LOCALAPPDATA%\Optimisation_Pilotage\data\meetings.sqlite`), donc plus d'erreur `sqlite3.OperationalError: unable to open database file`.
- L'app et le workflow GitHub restent identiques côté usage.
