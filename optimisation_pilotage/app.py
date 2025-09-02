import tkinter as tk
from tkinter import ttk, messagebox
from .modules import db, utils

def main():
    db.init_db()  # ensure schema
    utils.ensure_dirs()

    root = tk.Tk()
    root.title("CHAP1 – Compte-rendus Harmonises et Assistance au Pilotage 1 (v2.3.2)")
    root.geometry("900x600")

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)

    # Tabs
    tab_live = ttk.Frame(nb)
    tab_cr = ttk.Frame(nb)
    tab_export = ttk.Frame(nb)
    tab_settings = ttk.Frame(nb)

    nb.add(tab_live, text="Live (Mix)")
    nb.add(tab_cr, text="CR & ToDo")
    nb.add(tab_export, text="Export")
    nb.add(tab_settings, text="Paramètres")

    # Live placeholder
    ttk.Label(tab_live, text="Live Mix (placeholder) – l'exécutable se lance correctement.\nLes fonctionnalités avancées viendront via les prochaines mises à jour.", anchor="w").pack(padx=16, pady=16, fill="x")

    # CR & ToDo tables (empty for now, schema-ready)
    ttk.Label(tab_cr, text="Vue CR & ToDo (placeholder)").pack(padx=16, pady=16, anchor="w")

    # Export
    ttk.Label(tab_export, text="Exports (placeholder)").pack(padx=16, pady=16, anchor="w")

    # Settings
    info = (
        f"Dossiers:\n"
        f"  DATA: {utils.DATA_DIR}\n"
        f"  EXPORTS: {utils.EXPORTS_DIR}\n"
        f"  LOGS: {utils.LOGS_DIR}\n"
        f"  AUTOSAVE: {utils.AUTOSAVE_DIR}\n\n"
        "Icône embarquée, workflow corrigé."
    )
    ttk.Label(tab_settings, text=info, justify="left").pack(padx=16, pady=16, anchor="w")

    root.mainloop()