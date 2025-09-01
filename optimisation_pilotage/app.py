import sys, shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QFileDialog, QMessageBox, QMainWindow, QLabel, QLineEdit, QTextEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QSpinBox, QInputDialog, QGroupBox, QFrame
)
from PySide6.QtCore import QDate, QTimer, Qt, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QFont, QPen, QPainterPath, QIcon

from .modules import db, utils, parsing, export as export_mod, whisper_transcribe as wt
from .modules.live_capture import LiveConfig, LiveTranscriber
from .modules.models_manager import ModelManager

DATA_DIR = utils.DATA_DIR
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
EXPORTS_DIR = utils.EXPORTS_DIR
MODELS_DIR = utils.MODELS_DIR
for p in [DATA_DIR, AUDIO_DIR, TRANSCRIPTS_DIR, EXPORTS_DIR, MODELS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

DEFAULT_THEME = "Pilotage"
DEFAULT_PROJECT = "Général"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            db.init_db()
        except Exception as e:
            QMessageBox.critical(self, "Erreur base de données",
                                 f"Impossible d'initialiser la base.\n{e}\n\n"
                                 f"Essayez de relancer. Un log peut se trouver dans le dossier temporaire utilisateur.")
            raise

        self.setWindowTitle("CHAP1 — Compte-rendus Harmonisés et Assistance au Pilotage 1")
        # Set window icon from asset
        ico = utils.resource_path("assets/chap1.ico")
        self.setWindowIcon(QIcon(ico))

        self.resize(1140, 820)

        self.transcriber = None
        self.selected_audio = None
        self.current_mid = None
        self.last_live = None
        self.want_wav = False

        self.model_mgr = ModelManager(MODELS_DIR, on_change=self._refresh_status_tab)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(8,8,8,8)
        self.container_layout.setSpacing(8)

        self.header = self._build_header()
        self.container_layout.addWidget(self.header)

        self.tabs = QTabWidget()
        self.container_layout.addWidget(self.tabs, 1)

        self.setCentralWidget(self.container)

        self._build_tab_live()
        self._build_tab_file_notes()
        self._build_tab_meetings()
        self._build_tab_todo()
        self._build_tab_export()
        self._build_tab_status()

        self._ensure_defaults()
        self._load_side_data()
        self._select_defaults_everywhere()

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(2000)
        self._status_timer.timeout.connect(self._refresh_status_tab)
        self._status_timer.start()

    # ---------- Header / Logo
    def _build_header(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w); lay.setContentsMargins(6,6,6,6)
        self.logo_label = QLabel()
        self.logo_label.setFixedHeight(76)
        self.logo_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lay.addWidget(self.logo_label, 0, Qt.AlignLeft)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setFrameShadow(QFrame.Sunken)
        lay.addWidget(sep, 1)
        self._set_header_logo()
        return w

    def _default_logo_pixmap(self) -> QPixmap:
        w, h = 520, 76
        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, w-1, h-1), 14, 14)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor("#0a2a6a"))
        grad.setColorAt(0.5, QColor("#124fb6"))
        grad.setColorAt(1.0, QColor("#1f9dff"))
        p.fillPath(path, grad)
        p.setPen(QPen(QColor(255,255,255,80), 1.2))
        p.drawPath(path)

        cx, cy, r = 44, h//2, 26
        emblem = QPainterPath()
        emblem.addEllipse(QRectF(cx-r, cy-r, 2*r, 2*r))
        p.fillPath(emblem, QColor(255,255,255,40))
        p.setPen(QPen(QColor(255,255,255,160), 2))
        p.drawPath(emblem)
        f1 = QFont("Segoe UI", 16, QFont.DemiBold); f1.setLetterSpacing(QFont.PercentageSpacing, 102)
        p.setFont(f1); p.setPen(QColor("white"))
        p.drawText(QRectF(cx-r, cy-16, 2*r, 32), Qt.AlignCenter, "C1")

        f2 = QFont("Segoe UI", 24, QFont.Bold)
        f2.setLetterSpacing(QFont.PercentageSpacing, 102)
        p.setFont(f2)
        p.setPen(QColor("white"))
        p.drawText(QRectF(90, 14, w-100, 30), Qt.AlignVCenter | Qt.AlignLeft, "CHAP1")
        f3 = QFont("Segoe UI", 13, QFont.Normal)
        f3.setLetterSpacing(QFont.PercentageSpacing, 100)
        p.setFont(f3)
        p.setPen(QColor(240,240,240))
        p.drawText(QRectF(90, 40, w-100, 24), Qt.AlignVCenter | Qt.AlignLeft, "Compte-rendus Harmonisés et Assistance au Pilotage 1")

        p.end()
        return pm

    def _set_header_logo(self):
        custom = DATA_DIR / "custom_logo.png"
        if custom.exists():
            pm = QPixmap(str(custom))
            if not pm.isNull():
                self.logo_label.setPixmap(pm.scaledToHeight(76, Qt.SmoothTransformation))
                return
        asset_path = utils.resource_path("assets/logo.png")
        apm = QPixmap(asset_path)
        if not apm.isNull():
            self.logo_label.setPixmap(apm.scaledToHeight(76, Qt.SmoothTransformation))
            return
        self.logo_label.setPixmap(self._default_logo_pixmap())

    # --------- Helper methods and other tabs (unchanged from previous versions) ---------
    def _load_projects_for(self, theme_id, combo):
        combo.clear(); combo.addItem("— Sélectionner —", userData=None)
        if theme_id:
            for pid, th, name in db.list_projects(theme_id):
                combo.addItem(name, userData=pid)

    def _current_ids(self, cb_theme, cb_proj):
        return cb_theme.currentData(), cb_proj.currentData()

    def _ensure_defaults(self):
        themes = db.list_themes()
        theme_id = None
        for tid, name in themes:
            if name == "Pilotage":
                theme_id = tid
                break
        if theme_id is None:
            db.create_theme("Pilotage")
            themes = db.list_themes()
            for tid, name in themes:
                if name == "Pilotage":
                    theme_id = tid
                    break
        projs = db.list_projects(theme_id)
        has_proj = any(p[2] == "Général" for p in projs)
        if not has_proj:
            db.create_project(theme_id, "Général")

    def _select_defaults_everywhere(self):
        for cb in [self.cb_theme_live, self.cb_theme, self.cb_theme_meet, self.cb_theme_todo, self.cb_theme_export]:
            idx = cb.findText("Pilotage")
            if idx >= 0:
                cb.setCurrentIndex(idx)
        for cb in [self.cb_project_live, self.cb_project, self.cb_project_meet, self.cb_project_todo, self.cb_project_export]:
            idx = cb.findText("Général")
            if idx >= 0:
                cb.setCurrentIndex(idx)

    def _load_side_data(self):
        self.themes = db.list_themes()
        for cb in [self.cb_theme_live, self.cb_theme, self.cb_theme_meet, self.cb_theme_todo, self.cb_theme_export]:
            cb.clear(); cb.addItem("— Sélectionner —", userData=None)
        for tid, name in self.themes:
            for cb in [self.cb_theme_live, self.cb_theme, self.cb_theme_meet, self.cb_theme_todo, self.cb_theme_export]:
                cb.addItem(name, userData=tid)

    # ---------- UI: Live
    def _build_tab_live(self):
        from PySide6.QtWidgets import QVBoxLayout
        w = QWidget(); layout = QVBoxLayout(w)

        line1 = QHBoxLayout()
        self.cb_theme_live = QComboBox(); self.cb_project_live = QComboBox()
        self.cb_theme_live.currentIndexChanged.connect(lambda _: self._load_projects_for(self.cb_theme_live.currentData(), self.cb_project_live))
        btn_add_theme = QPushButton("➕ Thématique"); btn_add_proj = QPushButton("➕ Projet")
        btn_add_theme.clicked.connect(self._add_theme_dialog)
        btn_add_proj.clicked.connect(lambda: self._add_project_dialog(self.cb_theme_live.currentData()))
        line1.addWidget(QLabel("Thématique")); line1.addWidget(self.cb_theme_live)
        line1.addWidget(QLabel("Projet")); line1.addWidget(self.cb_project_live)
        line1.addWidget(btn_add_theme); line1.addWidget(btn_add_proj)
        layout.addLayout(line1)

        opts = QHBoxLayout()
        self.de_date_live = QDateEdit(); self.de_date_live.setDate(QDate.currentDate())
        self.sb_chunk = QSpinBox(); self.sb_chunk.setRange(12, 18); self.sb_chunk.setValue(15)
        self.cb_model = QComboBox(); self.cb_model.addItems(["small","medium"]); self.cb_model.setCurrentText("medium")
        self.le_title_live = QLineEdit("Réunion en direct")
        self.le_parts_live = QLineEdit("")
        opts.addWidget(QLabel("Modèle")); opts.addWidget(self.cb_model)
        l_chunk = QLabel("Fenêtre audio (s)"); l_chunk.setToolTip("Taille du segment envoyé au modèle. Plus grand = meilleure cohérence, plus petit = plus réactif.")
        opts.addWidget(l_chunk); opts.addWidget(self.sb_chunk)
        opts.addWidget(QLabel("Titre")); opts.addWidget(self.le_title_live)
        opts.addWidget(QLabel("Date")); opts.addWidget(self.de_date_live)
        layout.addLayout(opts)
        layout.addWidget(QLabel("Participants (optionnel)")); layout.addWidget(self.le_parts_live)

        def _on_model_change():
            if self.cb_model.currentText() == "small":
                self.sb_chunk.setRange(12, 18)
                if self.sb_chunk.value() < 12 or self.sb_chunk.value() > 18:
                    self.sb_chunk.setValue(15)
            else:
                self.sb_chunk.setRange(20, 30)
                if self.sb_chunk.value() < 20 or self.sb_chunk.value() > 30:
                    self.sb_chunk.setValue(20)
        self.cb_model.currentTextChanged.connect(lambda _: _on_model_change())
        _on_model_change()

        b = QHBoxLayout()
        self.btn_start = QPushButton("▶️ Démarrer (MIX Micro + Système)")
        self.btn_stop = QPushButton("⏹ Arrêter & enregistrer")
        self.btn_reset = QPushButton("🧹 Réinitialiser")
        self.btn_wav = QPushButton("⏺ Enregistrer WAV (OFF)")
        self.btn_start.clicked.connect(self._live_start)
        self.btn_stop.clicked.connect(self._live_stop)
        self.btn_reset.clicked.connect(self._live_reset)
        self.btn_wav.clicked.connect(self._toggle_wav)
        b.addWidget(self.btn_start); b.addWidget(self.btn_stop); b.addWidget(self.btn_reset); b.addWidget(self.btn_wav)
        layout.addLayout(b)

        self.te_live = QTextEdit(); self.te_live.setReadOnly(True)
        layout.addWidget(QLabel("Transcription"))
        layout.addWidget(self.te_live)

        self.btn_add_actions_live = QPushButton("➕ Ajouter actions détectées à la ToDo (Live)")
        self.btn_add_actions_live.setEnabled(False)
        self.btn_add_actions_live.clicked.connect(self._add_actions_from_last_live)
        layout.addWidget(self.btn_add_actions_live)

        self.tabs.addTab(w, "Live (MIX)")

    def _add_theme_dialog(self):
        name, ok = QInputDialog.getText(self, "Nouvelle thématique", "Nom :")
        if ok and name.strip():
            db.create_theme(name.strip())
            self._load_side_data()

    def _add_project_dialog(self, theme_id):
        if not theme_id:
            QMessageBox.information(self, "Projet", "Choisissez d'abord une thématique.")
            return
        name, ok = QInputDialog.getText(self, "Nouveau projet", "Nom :")
        if ok and name.strip():
            db.create_project(theme_id, name.strip())
            self._load_projects_for(theme_id, self.cb_project_live)
            self._load_projects_for(theme_id, self.cb_project)
            self._load_projects_for(theme_id, self.cb_project_meet)
            self._load_projects_for(theme_id, self.cb_project_todo)
            self._load_projects_for(theme_id, self.cb_project_export)

    def _on_live_update(self, state):
        if state.last_error:
            QMessageBox.critical(self, "Erreur Live", state.last_error)
        self.te_live.setPlainText(state.transcript)
        self.te_live.verticalScrollBar().setValue(self.te_live.verticalScrollBar().maximum())

    def _toggle_wav(self):
        if self.transcriber and self.transcriber.state.is_running:
            QMessageBox.information(self, "WAV", "Active/désactive l'enregistrement avant de démarrer le live.")
            return
        self.want_wav = not self.want_wav
        self.btn_wav.setText("⏺ Enregistrer WAV (ON)" if self.want_wav else "⏺ Enregistrer WAV (OFF)")

    def _ensure_model_present(self, size: str) -> bool:
        p = MODELS_DIR / f"faster-whisper-{size}"
        if p.exists() and any(p.iterdir()):
            return True
        ret = QMessageBox.question(self, "Modèle absent",
                                   f"Le modèle '{size}' n'est pas encore installé.\n"
                                   f"Voulez-vous ouvrir l'onglet 'État & Dossiers' pour le télécharger maintenant ?")
        if ret:
            self.tabs.setCurrentWidget(self.tab_status)
        return False

    def _live_start(self):
        th, pr = self._current_ids(self.cb_theme_live, self.cb_project_live)
        if not th or not pr:
            QMessageBox.warning(self, "Info", "Sélectionnez une Thématique et un Projet.")
            return
        size = self.cb_model.currentText()
        if not self._ensure_model_present(size):
            return
        wav_path = None
        if self.want_wav:
            folder = AUDIO_DIR / f"{th}_{pr}"; folder.mkdir(parents=True, exist_ok=True)
            fname = f"{self.de_date_live.date().toString('yyyyMMdd')}_{utils.slugify(self.le_title_live.text() or 'Reunion')}.wav"
            wav_path = str(folder / fname)
        cfg = LiveConfig(model_size=size, chunk_seconds=self.sb_chunk.value(), language="fr",
                         record_wav=self.want_wav, wav_path=wav_path)
        self.transcriber = LiveTranscriber(cfg, on_update=self._on_live_update)
        self.transcriber.start()
        self.btn_add_actions_live.setEnabled(False)
        self.last_live = None
        QMessageBox.information(self, "Live", f"Capture démarrée (MIX){' + WAV' if self.want_wav else ''}. Laissez la fenêtre ouverte.")

    def _live_stop(self):
        try:
            if self.transcriber:
                self.transcriber.stop()
        except Exception:
            pass
        text = self.te_live.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Live", "Aucune transcription à enregistrer.")
            return
        th, pr = self._current_ids(self.cb_theme_live, self.cb_project_live)
        title = self.le_title_live.text().strip() or "Réunion en direct"
        date = self.de_date_live.date().toString("yyyy-MM-dd")
        parts = self.le_parts_live.text().strip()

        folder = TRANSCRIPTS_DIR / f"{th}_{pr}"; folder.mkdir(parents=True, exist_ok=True)
        fname = f"{self.de_date_live.date().toString('yyyyMMdd')}_{utils.slugify(title)}.txt"
        fpath = folder / fname
        utils.save_text_to_file(text, fpath)
        mid = db.create_meeting(th, pr, title, date, parts, "teams", str(fpath), "")
        wav_path = self.transcriber.state.wav_path if self.transcriber else None
        self.last_live = {"th": th, "pr": pr, "mid": mid, "text": text, "wav_path": wav_path}
        self.btn_add_actions_live.setEnabled(True)
        msg = f"CR enregistré (Meeting ID: {mid})."
        if wav_path:
            msg += f"\nWAV : {wav_path}"
        QMessageBox.information(self, "Enregistré", msg)

    def _live_reset(self):
        try:
            if self.transcriber:
                self.transcriber.stop()
        except Exception:
            pass
        self.te_live.clear()
        self.last_live = None
        self.btn_add_actions_live.setEnabled(False)

    def _add_actions_from_last_live(self):
        if not self.last_live:
            QMessageBox.information(self, "Actions", "Aucun CR Live récent.")
            return
        text = self.last_live["text"]
        th = self.last_live["th"]; pr = self.last_live["pr"]; mid = self.last_live["mid"]
        known = db.get_setting("known_actors","")
        known_actors = [a.strip() for a in known.split(",") if a.strip()]
        suggestions = parsing.extract_actions(text, known_actors=known_actors)
        if not suggestions:
            QMessageBox.information(self, "Actions", "Aucune action détectée.")
            return
        for s in suggestions:
            db.create_todo(th, pr, mid, s["action"], s.get("actor",""), s.get("due_date",""))
        QMessageBox.information(self, "Actions", f"{len(suggestions)} action(s) ajoutée(s) à la ToDo.")

    # ---------- UI: Fichier / Notes
    def _build_tab_file_notes(self):
        w = QWidget(); layout = QVBoxLayout(w)

        line1 = QHBoxLayout()
        self.cb_theme = QComboBox(); self.cb_project = QComboBox()
        self.cb_theme.currentIndexChanged.connect(lambda _: self._load_projects_for(self.cb_theme.currentData(), self.cb_project))
        btn_add_theme = QPushButton("➕ Thématique"); btn_add_proj = QPushButton("➕ Projet")
        btn_add_theme.clicked.connect(self._add_theme_dialog)
        btn_add_proj.clicked.connect(lambda: self._add_project_dialog(self.cb_theme.currentData()))
        line1.addWidget(QLabel("Thématique")); line1.addWidget(self.cb_theme)
        line1.addWidget(QLabel("Projet")); line1.addWidget(self.cb_project)
        line1.addWidget(btn_add_theme); line1.addWidget(btn_add_proj)
        layout.addLayout(line1)

        meta = QHBoxLayout()
        self.de_date2 = QDateEdit(); self.de_date2.setDate(QDate.currentDate())
        self.le_title2 = QLineEdit("Réunion sans titre")
        self.le_parts2 = QLineEdit("")
        meta.addWidget(QLabel("Titre")); meta.addWidget(self.le_title2)
        meta.addWidget(QLabel("Date")); meta.addWidget(self.de_date2)
        layout.addLayout(meta)
        layout.addWidget(QLabel("Participants (optionnel)")); layout.addWidget(self.le_parts2)

        ar = QHBoxLayout()
        self.btn_pick_file = QPushButton("📁 Importer un audio (WAV)")
        self.btn_transcribe_file = QPushButton("▶️ Transcrire le fichier (offline)")
        self.btn_save_cr = QPushButton("💾 Enregistrer le CR")
        self.btn_pick_file.clicked.connect(self._pick_audio)
        self.btn_transcribe_file.clicked.connect(self._transcribe_audio)
        self.btn_save_cr.clicked.connect(self._save_file_notes_cr)
        ar.addWidget(self.btn_pick_file); ar.addWidget(self.btn_transcribe_file); ar.addWidget(self.btn_save_cr)
        layout.addLayout(ar)

        self.te_notes = QTextEdit(); self.te_notes.setPlaceholderText("Coller vos notes ici si pas d'audio…")
        layout.addWidget(QLabel("Contenu / Transcription"))
        layout.addWidget(self.te_notes)

        self.tabs.addTab(w, "Fichier / Notes")

    def _pick_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un WAV", "", "WAV (*.wav)")
        if path:
            self.selected_audio = path
            QMessageBox.information(self, "Fichier", f"Fichier sélectionné : {Path(path).name}")

    def _transcribe_audio(self):
        try:
            path = getattr(self, "selected_audio", None)
            if not path:
                QMessageBox.warning(self, "Info", "Aucun fichier choisi.")
                return
            text = wt.transcribe_offline_faster(path, language="fr", model_size="medium")
            self.te_notes.setPlainText(text)
            QMessageBox.information(self, "Transcription", "Terminé.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur transcription", str(e))

    def _save_file_notes_cr(self):
        th, pr = self._current_ids(self.cb_theme, self.cb_project)
        if not th or not pr:
            QMessageBox.warning(self, "Info", "Sélectionnez une Thématique et un Projet.")
            return
        text = self.te_notes.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Info", "Aucun contenu à enregistrer.")
            return
        title = self.le_title2.text().strip() or "Réunion sans titre"
        date = self.de_date2.date().toString("yyyy-MM-dd")
        parts = self.le_parts2.text().strip()

        folder = TRANSCRIPTS_DIR / f"{th}_{pr}"; folder.mkdir(parents=True, exist_ok=True)
        fname = f"{self.de_date2.date().toString('yyyyMMdd')}_{utils.slugify(title)}.txt"
        fpath = folder / fname
        utils.save_text_to_file(text, fpath)
        mid = db.create_meeting(th, pr, title, date, parts, "audio" if getattr(self, "selected_audio", None) else "manuel", str(fpath), "")
        QMessageBox.information(self, "Enregistré", f"CR enregistré (Meeting ID: {mid}).")

        known = db.get_setting("known_actors","")
        known_actors = [a.strip() for a in known.split(",") if a.strip()]
        suggestions = parsing.extract_actions(text, known_actors=known_actors)
        if suggestions:
            for s in suggestions:
                db.create_todo(th, pr, mid, s["action"], s.get("actor",""), s.get("due_date",""))
            QMessageBox.information(self, "ToDo", f"{len(suggestions)} action(s) ajoutée(s).")

    # ---------- UI: Meetings
    def _build_tab_meetings(self):
        w = QWidget(); layout = QVBoxLayout(w)

        line1 = QHBoxLayout()
        self.cb_theme_meet = QComboBox(); self.cb_project_meet = QComboBox()
        self.cb_theme_meet.currentIndexChanged.connect(lambda _: self._load_projects_for(self.cb_theme_meet.currentData(), self.cb_project_meet))
        self.le_search = QLineEdit(""); self.le_search.setPlaceholderText("Rechercher dans les titres / résumés…")
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.clicked.connect(self._refresh_meetings)
        line1.addWidget(QLabel("Thématique")); line1.addWidget(self.cb_theme_meet)
        line1.addWidget(QLabel("Projet")); line1.addWidget(self.cb_project_meet)
        line1.addWidget(self.le_search); line1.addWidget(btn_refresh)
        layout.addLayout(line1)

        self.tbl_meet = QTableWidget(0, 5)
        self.tbl_meet.setHorizontalHeaderLabels(["ID","Titre","Date","Participants","Source"])
        self.tbl_meet.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_meet.cellClicked.connect(self._open_meeting)
        layout.addWidget(self.tbl_meet)

        self.te_meet = QTextEdit(); layout.addWidget(self.te_meet)

        meta = QHBoxLayout()
        self.le_meet_parts = QLineEdit("")
        btn_save_meta = QPushButton("💾 Sauvegarder participants")
        btn_save_meta.clicked.connect(self._save_meeting_meta)
        meta.addWidget(QLabel("Participants")); meta.addWidget(self.le_meet_parts); meta.addWidget(btn_save_meta)
        layout.addLayout(meta)

        btns = QHBoxLayout()
        btn_save = QPushButton("💾 Enregistrer le contenu")
        btn_actions = QPushButton("🔎 Détecter → ToDo")
        btn_save.clicked.connect(self._save_meeting_content)
        btn_actions.clicked.connect(self._detect_actions_current)
        btns.addWidget(btn_save); btns.addWidget(btn_actions)
        layout.addLayout(btns)

        self.tabs.addTab(w, "CR & Notes")

    def _refresh_meetings(self):
        th = self.cb_theme_meet.currentData()
        pr = self.cb_project_meet.currentData()
        sch = self.le_search.text().strip() or None
        rows = db.list_meetings(th, pr, sch)
        self.tbl_meet.setRowCount(0)
        for m in rows:
            r = self.tbl_meet.rowCount()
            self.tbl_meet.insertRow(r)
            for c, val in enumerate([m[0], m[3], m[4], m[5] or "", m[6] or ""]):
                self.tbl_meet.setItem(r, c, QTableWidgetItem(str(val)))
        if rows:
            self.tbl_meet.selectRow(0)
            self._open_meeting(0, 0)

    def _open_meeting(self, row, col):
        try:
            mid = int(self.tbl_meet.item(row, 0).text())
            m = db.get_meeting(mid)
            if not m: return
            content = utils.read_text_file(m[8] or "")
            self.te_meet.setPlainText(content)
            self.le_meet_parts.setText(m[5] or "")
            self.current_mid = mid
        except Exception:
            pass

    def _save_meeting_meta(self):
        mid = getattr(self, "current_mid", None)
        if not mid: return
        db.update_meeting(mid, participants=self.le_meet_parts.text().strip())
        QMessageBox.information(self, "CR", "Participants mis à jour.")

    def _save_meeting_content(self):
        mid = getattr(self, "current_mid", None)
        if not mid: return
        m = db.get_meeting(mid)
        if m and m[8]:
            utils.save_text_to_file(self.te_meet.toPlainText(), m[8])
            QMessageBox.information(self, "CR", "Contenu mis à jour.")

    def _detect_actions_current(self):
        mid = getattr(self, "current_mid", None)
        if not mid: return
        m = db.get_meeting(mid); text = self.te_meet.toPlainText()
        known = db.get_setting("known_actors","")
        known_actors = [a.strip() for a in known.split(",") if a.strip()]
        sugg = parsing.extract_actions(text, known_actors=known_actors)
        if sugg:
            for s in sugg:
                db.create_todo(m[1], m[2], mid, s["action"], s.get("actor",""), s.get("due_date",""))
            QMessageBox.information(self, "ToDo", f"{len(sugg)} action(s) ajoutée(s).")
        else:
            QMessageBox.information(self, "ToDo", "Aucune action détectée.")

    # ---------- UI: ToDo
    def _build_tab_todo(self):
        w = QWidget(); layout = QVBoxLayout(w)
        line = QHBoxLayout()
        self.cb_theme_todo = QComboBox(); self.cb_project_todo = QComboBox()
        self.cb_theme_todo.currentIndexChanged.connect(lambda _: self._load_projects_for(self.cb_theme_todo.currentData(), self.cb_project_todo))
        self.cb_status = QComboBox(); self.cb_status.addItems(["Tous","Ouvert","Clos"])
        self.le_search_todo = QLineEdit(""); self.le_search_todo.setPlaceholderText("Rechercher (action/acteur)…")
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.clicked.connect(self._refresh_todo)
        line.addWidget(QLabel("Thématique")); line.addWidget(self.cb_theme_todo)
        line.addWidget(QLabel("Projet")); line.addWidget(self.cb_project_todo)
        line.addWidget(QLabel("Statut")); line.addWidget(self.cb_status)
        line.addWidget(self.le_search_todo); line.addWidget(btn_refresh)
        layout.addLayout(line)

        self.tbl_todo = QTableWidget(0, 7)
        self.tbl_todo.setHorizontalHeaderLabels(["ID","MeetingID","Action","Acteur","Échéance","Statut","Créé"])
        self.tbl_todo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tbl_todo)

        editor = QHBoxLayout()
        self.le_actor = QLineEdit("")
        self.le_due = QLineEdit("")
        self.cb_stat2 = QComboBox(); self.cb_stat2.addItems(["Ouvert","Clos"])
        btn_save = QPushButton("💾 Mettre à jour")
        btn_save.clicked.connect(self._save_todo)
        editor.addWidget(QLabel("Acteur")); editor.addWidget(self.le_actor)
        editor.addWidget(QLabel("Échéance (YYYY-MM-DD)")); editor.addWidget(self.le_due)
        editor.addWidget(QLabel("Statut")); editor.addWidget(self.cb_stat2); editor.addWidget(btn_save)
        layout.addLayout(editor)

        self.tabs.addTab(w, "ToDo")

    def _refresh_todo(self):
        th = self.cb_theme_todo.currentData()
        pr = self.cb_project_todo.currentData()
        status = self.cb_status.currentText()
        search = self.le_search_todo.text().strip() or None
        rows = db.list_todos(th, pr, None if status=="Tous" else status, search=search)
        self.tbl_todo.setRowCount(0)
        for t in rows:
            r = self.tbl_todo.rowCount()
            self.tbl_todo.insertRow(r)
            for c, val in enumerate([t[0], t[3] or "", t[4], t[5] or "", t[6] or "", t[7], t[8]]):
                self.tbl_todo.setItem(r, c, QTableWidgetItem(str(val)))
        if rows:
            self.tbl_todo.selectRow(0)
            self._load_todo_editor_from_row(0)
        self.tbl_todo.cellClicked.connect(self._load_todo_editor_from_row)

    def _load_todo_editor_from_row(self, row, col=0):
        try:
            actor = self.tbl_todo.item(row, 3).text()
            due = self.tbl_todo.item(row, 4).text()
            status = self.tbl_todo.item(row, 5).text()
            self.le_actor.setText(actor); self.le_due.setText(due); self.cb_stat2.setCurrentText(status)
        except Exception:
            pass

    def _save_todo(self):
        row = self.tbl_todo.currentRow()
        if row < 0: return
        todo_id = int(self.tbl_todo.item(row, 0).text())
        db.update_todo(todo_id, actor=self.le_actor.text().strip(), due_date=self.le_due.text().strip(), status=self.cb_stat2.currentText())
        QMessageBox.information(self, "ToDo", "Action mise à jour.")

    # ---------- UI: Export
    def _build_tab_export(self):
        w = QWidget(); layout = QVBoxLayout(w)
        line1 = QHBoxLayout()
        self.cb_theme_export = QComboBox(); self.cb_project_export = QComboBox()
        self.cb_theme_export.currentIndexChanged.connect(lambda _: self._load_projects_for(self.cb_theme_export.currentData(), self.cb_project_export))
        btn_export = QPushButton("📤 Export CR + ToDo (Excel)")
        btn_export.clicked.connect(self._do_export)
        line1.addWidget(QLabel("Thématique")); line1.addWidget(self.cb_theme_export)
        line1.addWidget(QLabel("Projet")); line1.addWidget(self.cb_project_export)
        line1.addWidget(btn_export)
        layout.addLayout(line1)
        self.tabs.addTab(w, "Exports")

    def _do_export(self):
        th = self.cb_theme_export.currentData()
        pr = self.cb_project_export.currentData()
        path = export_mod.export_excel(th, pr)
        QMessageBox.information(self, "Export", f"Fichier généré : {path}")

    # ---------- UI: Status & folders
    def _build_tab_status(self):
        w = QWidget(); layout = QVBoxLayout(w)

        box_m = QGroupBox("Modèles Whisper")
        mlay = QVBoxLayout(box_m)

        self.lbl_small = QLabel("Small : état inconnu")
        self.btn_small = QPushButton("Télécharger Small")
        self.btn_small.clicked.connect(lambda: self._dl_model('small'))

        self.lbl_medium = QLabel("Medium : état inconnu")
        self.btn_medium = QPushButton("Télécharger Medium")
        self.btn_medium.clicked.connect(lambda: self._dl_model('medium'))

        mlay.addWidget(self.lbl_small); mlay.addWidget(self.btn_small)
        mlay.addWidget(self.lbl_medium); mlay.addWidget(self.btn_medium)

        box_d = QGroupBox("Dossiers & Logo")
        dlay = QVBoxLayout(box_d)
        self.btn_open_cr = QPushButton("Ouvrir dossier CR (transcripts)")
        self.btn_open_exports = QPushButton("Ouvrir dossier Exports")
        self.btn_open_models = QPushButton("Ouvrir dossier Modèles")
        self.btn_open_db = QPushButton("Ouvrir dossier Base de données")
        self.btn_pick_logo = QPushButton("Choisir un logo personnalisé…")
        self.btn_open_cr.clicked.connect(lambda: utils.open_folder(TRANSCRIPTS_DIR))
        self.btn_open_exports.clicked.connect(lambda: utils.open_folder(EXPORTS_DIR))
        self.btn_open_models.clicked.connect(lambda: utils.open_folder(MODELS_DIR))
        self.btn_open_db.clicked.connect(lambda: utils.open_folder(DATA_DIR))
        self.btn_pick_logo.clicked.connect(self._pick_logo)

        dlay.addWidget(self.btn_open_cr)
        dlay.addWidget(self.btn_open_exports)
        dlay.addWidget(self.btn_open_models)
        dlay.addWidget(self.btn_open_db)
        dlay.addWidget(self.btn_pick_logo)

        layout.addWidget(box_m)
        layout.addWidget(box_d)
        layout.addStretch()
        self.tabs.addTab(w, "État & Dossiers")
        self.tab_status = w
        self._refresh_status_tab()

    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un logo (PNG/JPG)", "", "Images (*.png *.jpg *.jpeg)")
        if not path: return
        dest = DATA_DIR / "custom_logo.png"
        try:
            shutil.copyfile(path, dest)
            self._set_header_logo()
            QMessageBox.information(self, "Logo", "Logo mis à jour.")
        except Exception as e:
            QMessageBox.critical(self, "Logo", f"Impossible d'appliquer le logo : {e}")

    def _dl_model(self, which: str):
        if which == 'small':
            self.model_mgr.download_small()
        else:
            self.model_mgr.download_medium()
        self._refresh_status_tab()

    def _refresh_status_tab(self):
        self.model_mgr.refresh()
        s = self.model_mgr.status_small
        m = self.model_mgr.status_medium

        def text(st):
            if st.present: return f"{st.name} : Installé ({st.path})"
            if st.downloading: return f"{st.name} : Téléchargement en cours..."
            if st.error: return f"{st.name} : Erreur — {st.error}"
            return f"{st.name} : Non téléchargé"

        self.lbl_small.setText(text(s))
        self.lbl_medium.setText(text(m))

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
