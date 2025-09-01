import sys
from pathlib import Path
from datetime import datetime, date
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QDateEdit, QTextEdit,
    QListWidget, QFormLayout, QFileDialog, QMessageBox
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from .modules import db, utils
from .modules.export import export_excel
from .modules.models_manager import ModelManager
from .modules.whisper_transcribe import LiveMixTranscriber

def apply_global_styles(app):
    app.setStyleSheet(
        "QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {"
        "  background: #ffffff; color: #111111; padding: 6px;"
        "  border: 1px solid #cfd3da; border-radius: 6px;"
        "}"
        "QDateEdit::drop-down, QComboBox::drop-down { width: 24px; }"
        "QToolTip { color: #111111; background: #f5f7fa; border: 1px solid #cfd3da; }"
        "QPushButton { padding:8px 12px; }"
    )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CHAP1 — Compte-rendus Harmonises et Assistance au Pilotage 1")
        icon = Path(__file__).parent.parent/"assets/chap1.ico"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        db.init_db()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_tab_live_mix()
        self._build_tab_manage()
        self._build_tab_export()
        self._build_tab_status()

        self.model_mgr.refresh()
        self._on_model_change_default_passes()

        self.resize(1050, 720)

    # -------- Live Mix tab --------
    def _on_model_change_default_passes(self, idx=None):
        try:
            name = self.combo_model.currentText().lower()
        except Exception:
            return
        if "medium" in name:
            self.spin_pass.setRange(10, 60)
            if self.spin_pass.value() < 20 or self.spin_pass.value() > 30:
                self.spin_pass.setValue(25)
            self.lbl_pass_hint.setText("Conseil: 20–30 s (modèle medium)")
        else:
            self.spin_pass.setRange(8, 40)
            if self.spin_pass.value() < 12 or self.spin_pass.value() > 18:
                self.spin_pass.setValue(15)
            self.lbl_pass_hint.setText("Conseil: 12–18 s (modèle small)")

    def _build_tab_live_mix(self):
        w = QWidget(); layout = QVBoxLayout(w)

        row1 = QHBoxLayout()
        self.combo_model = QComboBox()
        self.combo_model.addItems(["faster-whisper-small", "faster-whisper-medium"])
        self.combo_model.currentIndexChanged.connect(self._on_model_change_default_passes)

        self.spin_pass = QSpinBox(); self.spin_pass.setValue(15)
        self.lbl_pass_hint = QLabel("")

        self.date_meet = QDateEdit()
        self.date_meet.setDate(datetime.now().date())
        self.date_meet.setCalendarPopup(True)

        row1.addWidget(QLabel("Modèle:")); row1.addWidget(self.combo_model,1)
        row1.addWidget(QLabel("Pas (s):")); row1.addWidget(self.spin_pass)
        row1.addWidget(QLabel("Date:")); row1.addWidget(self.date_meet)
        layout.addLayout(row1)
        layout.addWidget(self.lbl_pass_hint)

        row2 = QFormLayout()
        self.edit_title = QLineEdit(); self.edit_title.setPlaceholderText("Titre / Sujet de la réunion")
        self.combo_theme = QComboBox(); self.combo_project = QComboBox()
        self._refresh_theme_project()
        self.edit_participants = QLineEdit(); self.edit_participants.setPlaceholderText("Participants (séparés par des virgules)")
        row2.addRow("Thématique:", self.combo_theme)
        row2.addRow("Projet:", self.combo_project)
        row2.addRow("Titre:", self.edit_title)
        row2.addRow("Participants:", self.edit_participants)
        layout.addLayout(row2)

        # Transcription area
        self.txt_live = QTextEdit(); self.txt_live.setReadOnly(False)
        self.txt_live.setPlaceholderText("Transcription en cours... (modifiable)")
        layout.addWidget(self.txt_live, 1)

        btns = QHBoxLayout()
        self.btn_start = QPushButton("Démarrer (mix micro + système)")
        self.btn_stop = QPushButton("Arrêter")
        self.btn_stop.setEnabled(False)
        btns.addWidget(self.btn_start); btns.addWidget(self.btn_stop); btns.addStretch(1)
        layout.addLayout(btns)

        self.lbl_state = QLabel("État: prêt")
        layout.addWidget(self.lbl_state)

        self.tabs.addTab(w, "Live (Mix)")

        self.btn_start.clicked.connect(self._start_live)
        self.btn_stop.clicked.connect(self._stop_live)

        self._live = None

    def _refresh_theme_project(self):
        self.combo_theme.clear(); self.combo_project.clear()
        themes = db.list_themes()
        if not themes:
            db.create_theme("Général"); themes = db.list_themes()
            db.create_project(themes[0][0], "Par défaut")
        for t in themes:
            self.combo_theme.addItem(t[1], t[0])
        projects = db.list_projects(self.combo_theme.currentData())
        for p in projects:
            self.combo_project.addItem(p[2], p[0])
        self.combo_theme.currentIndexChanged.connect(self._reload_projects)

    def _reload_projects(self, idx):
        theme_id = self.combo_theme.currentData()
        self.combo_project.clear()
        for p in db.list_projects(theme_id):
            self.combo_project.addItem(p[2], p[0])

    def _start_live(self):
        theme_id = self.combo_theme.currentData()
        project_id = self.combo_project.currentData()
        title = self.edit_title.text().strip() or "Réunion"
        d = self.date_meet.date().toString("yyyy-MM-dd")
        participants = self.edit_participants.text().strip()

        # Create meeting row now
        meeting_id = db.create_meeting(theme_id, project_id, title, d, participants, "LiveMix", "", "")
        self._current_meeting_id = meeting_id

        # model path
        model_name = self.combo_model.currentText()
        models_dir = utils.MODELS_DIR
        self.model_mgr = getattr(self, "model_mgr", None) or ModelManager(models_dir, on_change=None)
        self.model_mgr.refresh()
        status = self.model_mgr.status_small if "small" in model_name else self.model_mgr.status_medium
        if not status.present:
            if "small" in model_name: self.model_mgr.download_small()
            else: self.model_mgr.download_medium()
            QMessageBox.information(self, "Téléchargement",
                "Le modèle Whisper n'est pas encore présent. Téléchargement lancé en arrière-plan.\nRelancez l'écoute quand le téléchargement est terminé (onglet Paramètres).")
            return

        def on_text(t):
            prev = self.txt_live.toPlainText()
            self.txt_live.setPlainText((prev + "\n" + t).strip())
            self.txt_live.moveCursor(self.txt_live.textCursor().End)

        def on_state(s):
            self.lbl_state.setText(f"État: {s}")

        from .modules.whisper_transcribe import LiveMixTranscriber
        self._live = LiveMixTranscriber(utils.MODELS_DIR, "small" if "small" in model_name else "medium",
                                        self.spin_pass.value(), on_text=on_text, on_state=on_state)
        self._live.start()
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)

    def _stop_live(self):
        if self._live:
            self._live.stop()
            self._live = None
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        # persist text to file + DB path
        if hasattr(self, "_current_meeting_id"):
            txt = self.txt_live.toPlainText().strip()
            p = utils.path_for_meeting_txt(self._current_meeting_id)
            p.write_text(txt, encoding="utf-8")
            db.update_meeting(self._current_meeting_id, transcript_path=str(p), summary=txt[:500])

    # -------- Manage tab (CR & ToDo) --------
    def _build_tab_manage(self):
        w = QWidget(); layout = QVBoxLayout(w)
        row = QHBoxLayout()
        self.list_meetings = QListWidget()
        self.btn_refresh = QPushButton("Rafraîchir")
        row.addWidget(self.list_meetings, 2)
        row2 = QVBoxLayout()
        self.txt_meeting = QTextEdit()
        row2.addWidget(QLabel("Contenu / CR (modifiable)"))
        row2.addWidget(self.txt_meeting, 1)
        save = QPushButton("Enregistrer les modifications")
        row2.addWidget(save)
        row.addLayout(row2, 3)
        layout.addLayout(row)
        self.tabs.addTab(w, "CR & ToDo")

        self.btn_refresh.clicked.connect(self._load_meetings)
        save.clicked.connect(self._save_current_meeting)
        layout.addWidget(self.btn_refresh)

        self.list_meetings.itemSelectionChanged.connect(self._load_selected)
        self._load_meetings()

    def _load_meetings(self):
        self.list_meetings.clear()
        for r in db.list_meetings():
            self.list_meetings.addItem(f"[{r[0]}] {r[3]} — {r[4]}")

    def _load_selected(self):
        it = self.list_meetings.currentItem()
        if not it: return
        mid = int(it.text().split("]")[0][1:])
        m = db.get_meeting(mid)
        if m:
            path = m[8] or ""
            txt = ""
            if path and Path(path).exists():
                try: txt = Path(path).read_text(encoding="utf-8")
                except Exception: txt = m[9] or ""
            else:
                txt = m[9] or ""
            self.txt_meeting.setPlainText(txt)

    def _save_current_meeting(self):
        it = self.list_meetings.currentItem()
        if not it: return
        mid = int(it.text().split("]")[0][1:])
        txt = self.txt_meeting.toPlainText()
        p = utils.path_for_meeting_txt(mid)
        p.write_text(txt, encoding="utf-8")
        db.update_meeting(mid, transcript_path=str(p), summary=txt[:500])
        QMessageBox.information(self, "Sauvegardé", "CR mis à jour.")

    # -------- Export tab --------
    def _build_tab_export(self):
        w = QWidget(); layout = QVBoxLayout(w)
        btn = QPushButton("Export : Excel (CR, ToDo, ToDo_Global)")
        layout.addWidget(btn)
        btn.clicked.connect(self._do_export)
        self.lbl_export = QLabel("")
        layout.addWidget(self.lbl_export)
        self.tabs.addTab(w, "Export")

    def _do_export(self):
        path = export_excel()
        self.lbl_export.setText(f"Exporté : {path}")

    # -------- Paramètres / Status --------
    def _build_tab_status(self):
        w = QWidget(); layout = QVBoxLayout(w)
        self.model_mgr = ModelManager(utils.MODELS_DIR, on_change=self._refresh_status_tab_ui)
        layout.addWidget(QLabel("Modèles Whisper (téléchargement hors-ligne pour usage rapide)"))

        row = QHBoxLayout()
        self.lbl_small = QLabel("Small: inconnu"); self.btn_small = QPushButton("Télécharger Small")
        row.addWidget(self.lbl_small); row.addWidget(self.btn_small); layout.addLayout(row)

        row2 = QHBoxLayout()
        self.lbl_med = QLabel("Medium: inconnu"); self.btn_med = QPushButton("Télécharger Medium")
        row2.addWidget(self.lbl_med); row2.addWidget(self.btn_med); layout.addLayout(row2)

        self.btn_open_data = QPushButton("Ouvrir dossier CR")
        layout.addWidget(self.btn_open_data)
        self.tabs.addTab(w, "Paramètres")

        self.btn_small.clicked.connect(self.model_mgr.download_small)
        self.btn_med.clicked.connect(self.model_mgr.download_medium)
        self.btn_open_data.clicked.connect(self._open_data_dir)

        self._refresh_status_tab_ui()

    def _refresh_status_tab_ui(self):
        self.model_mgr.refresh()
        s = self.model_mgr.status_small
        m = self.model_mgr.status_medium
        self.lbl_small.setText(f"Small: {'installé' if s.present else 'non installé'} — {s.path}")
        self.lbl_med.setText(f"Medium: {'installé' if m.present else 'non installé'} — {m.path}")

    def _open_data_dir(self):
        p = utils.DATA_DIR
        try:
            import subprocess, os
            if sys.platform.startswith("win"):
                os.startfile(str(p))
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception:
            QMessageBox.information(self, "Info", f"Dossier: {p}")

def main():
    app = QApplication(sys.argv)
    apply_global_styles(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
