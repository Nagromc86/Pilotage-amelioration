
import sys, datetime, re
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QComboBox, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QStatusBar, QShortcut, QInputDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence

from .modules import db
from .modules.utils import DATA_DIR, EXPORTS_DIR, MODELS_DIR, LOGS_DIR, AUTOSAVE_DIR, open_folder, get_logger
from .modules.models_manager import ModelsManager
from .modules.audio_mix import MixerRecorder
from .modules.whisper_transcribe import transcribe_file
from .modules.export import export_excel

log = get_logger()

def _err(msg):
    log.error(msg)
    QMessageBox.critical(None, 'Erreur', msg)

def sanitize(s):
    s = re.sub(r'[^A-Za-z0-9_\-]+','_', s.strip())
    return s.strip('_')

class MainWindow(QWidget):
    def __init__(self):
        super().__init__(); db.init_db()
        self.setWindowTitle('CHAP1 — Compte-rendus Harmonisés et Assistance au Pilotage 1'); self.resize(1150,760)
        self.tabs=QTabWidget()

        self._build_tab_live()
        self._build_tab_cr_todo()
        self._build_tab_export()
        self._build_tab_params()

        lay=QVBoxLayout(self); lay.addWidget(self.tabs)

        self.recorder=MixerRecorder(on_tick=self._on_record_tick)
        self.model_mgr=ModelsManager(on_change=self._refresh_status_tab)

        self.autosave_timer = QTimer(self); self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start(30000)

        QShortcut(QKeySequence('Ctrl+S'), self, activated=self._save_meeting)
        QShortcut(QKeySequence('Ctrl+R'), self, activated=self._toggle_record)

    # ==== LIVE (MIX) ====
    def _build_tab_live(self):
        w=QWidget(); lay=QVBoxLayout(w)
        self.status = QStatusBar(); lay.addWidget(self.status)

        l1=QHBoxLayout(); l1.addWidget(QLabel('Modèle:'))
        self.model_sel=QComboBox(); self.model_sel.addItems(['small','medium']); self.model_sel.currentTextChanged.connect(self._on_model_change); l1.addWidget(self.model_sel)
        l1.addWidget(QLabel('Fenêtre audio (s):')); self.window_s=QLineEdit('12'); self.window_s.setMaximumWidth(100); self.window_s.setStyleSheet('color:black;background:white;'); l1.addWidget(self.window_s)
        l1.addWidget(QLabel('Pas (s):')); self.pas_s=QLineEdit('3'); self.pas_s.setMaximumWidth(100); self.pas_s.setStyleSheet('color:black;background:white;'); l1.addWidget(self.pas_s)
        l1.addWidget(QLabel('Date:')); self.date_edit=QLineEdit(datetime.date.today().isoformat()); self.date_edit.setMaximumWidth(140); self.date_edit.setStyleSheet('color:black;background:white;'); l1.addWidget(self.date_edit)
        lay.addLayout(l1)

        # Audio devices
        try:
            import soundcard as sc
            mics = [m.name for m in sc.all_microphones(include_loopback=True)]
        except Exception:
            mics = []
        ldev=QHBoxLayout(); ldev.addWidget(QLabel('Micro:'))
        self.mic_sel=QComboBox(); self.mic_sel.addItems(mics or ['(défaut)']); ldev.addWidget(self.mic_sel)
        ldev.addWidget(QLabel('Système (loopback):'))
        self.sys_sel=QComboBox(); self.sys_sel.addItems(mics or ['(défaut)']); ldev.addWidget(self.sys_sel)
        lay.addLayout(ldev)

        l2=QHBoxLayout()
        self.btn_start=QPushButton('Démarrer (mix micro + système)'); self.btn_stop=QPushButton('Arrêter'); self.btn_trans=QPushButton('Transcrire')
        [l2.addWidget(b) for b in (self.btn_start,self.btn_stop,self.btn_trans)]; lay.addLayout(l2)
        self.btn_start.clicked.connect(self._start_mix); self.btn_stop.clicked.connect(self._stop_mix); self.btn_trans.clicked.connect(self._transcribe_last)

        self.cr_text=QTextEdit(); lay.addWidget(self.cr_text)
        self.lbl_wc=QLabel('Mots: 0'); lay.addWidget(self.lbl_wc)
        self.cr_text.textChanged.connect(self._update_word_count)

        l3=QHBoxLayout()
        self.thematique_in=QLineEdit(); self.thematique_in.setPlaceholderText('Thématique'); self.thematique_in.setStyleSheet('color:black;background:white;')
        self.projet_in=QLineEdit(); self.projet_in.setPlaceholderText('Projet'); self.projet_in.setStyleSheet('color:black;background:white;')
        self.participants_in=QLineEdit(); self.participants_in.setPlaceholderText('Participants (;)'); self.participants_in.setStyleSheet('color:black;background:white;')
        self.btn_save_meeting=QPushButton('Enregistrer le CR'); self.btn_save_meeting.clicked.connect(self._save_meeting)
        for it in (QLabel('Thématique:'), self.thematique_in, QLabel('Projet:'), self.projet_in, QLabel('Participants:'), self.participants_in, self.btn_save_meeting): l3.addWidget(it)
        lay.addLayout(l3)

        self.tab_live=w; self.tabs.addTab(w,'Live (Mix)')
        self._on_model_change(self.model_sel.currentText())

        self.ui_timer = QTimer(self); self.ui_timer.timeout.connect(self._tick_ui); self.ui_timer.start(1000)

    def _toggle_record(self):
        if getattr(self, '_is_rec', False):
            self._stop_mix()
        else:
            self._start_mix()

    def _tick_ui(self):
        wc = len(self.cr_text.toPlainText().split()); self.lbl_wc.setText(f'Mots: {wc}')
        if getattr(self, '_is_rec', False):
            secs = getattr(self, '_rec_secs', 0)
            self.status.showMessage(f'Enregistrement… {secs}s → {getattr(self, "_last_wav", "")}')
        else:
            self.status.showMessage('Prêt')

    def _on_model_change(self,name):
        if name=='small':
            self.window_s.setText(db.get_setting('small_window','12'))
            self.pas_s.setText(db.get_setting('small_pas','3'))
        else:
            self.window_s.setText(db.get_setting('medium_window','24'))
            self.pas_s.setText(db.get_setting('medium_pas','6'))

    def _on_record_tick(self, seconds): self._rec_secs = seconds

    def _start_mix(self):
        out=DATA_DIR/f"live_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        try:
            mic = self.mic_sel.currentText(); sysd = self.sys_sel.currentText()
            self.recorder.set_devices(mic, sysd)
            self._is_rec = True; self._rec_secs = 0
            self.recorder.start(out)
            self._last_wav = out
            QMessageBox.information(self,'Enregistrement',f'Enregistrement en cours → {out}')
        except Exception as e:
            self._is_rec = False
            _err(f"Impossible de démarrer l'enregistrement: {e}")

    def _stop_mix(self):
        try:
            path=self.recorder.stop(); self._is_rec=False
            QMessageBox.information(self,'Arrêt',f'Enregistrement sauvegardé: {path}'); self._last_wav=path
        except Exception as e:
            _err(f"Erreur à l'arrêt: {e}")

    def _transcribe_last(self):
        if not hasattr(self,'_last_wav'): _err('Aucun enregistrement trouvé.'); return
        model=self.model_sel.currentText()
        try:
            txt,info=transcribe_file(self._last_wav, model_size=model); self.cr_text.setPlainText(txt)
        except Exception as e: _err(f'Transcription impossible: {e}')

    def _autosave(self):
        try:
            AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
            (AUTOSAVE_DIR/'live_autosave.txt').write_text(self.cr_text.toPlainText(), encoding='utf-8')
        except Exception as e: log.error(f'Autosave error: {e}')

    def _auto_filename(self):
        date = self.date_edit.text().strip() or datetime.date.today().isoformat()
        th = sanitize(self.thematique_in.text() or 'NA')
        pr = sanitize(self.projet_in.text() or 'NA')
        title = sanitize(' '.join(self.cr_text.toPlainText().strip().split()[:6]) or 'CR')
        return f"{date}_{th}_{pr}_{title}.txt"

    def _save_meeting(self):
        date=self.date_edit.text().strip() or datetime.date.today().isoformat()
        the=self.thematique_in.text().strip(); prj=self.projet_in.text().strip(); part=self.participants_in.text().strip(); content=self.cr_text.toPlainText()
        con=db.get_conn(); cur=con.cursor()
        cur.execute('INSERT INTO meetings(date,thematique,projet,participants,content) VALUES (?,?,?,?,?)',(date,the,prj,part,content))
        con.commit(); con.close()
        try:
            (DATA_DIR/'CR').mkdir(exist_ok=True, parents=True)
            (DATA_DIR/'CR'/self._auto_filename()).write_text(content, encoding='utf-8')
        except Exception as e: log.error(f'Error writing CR file: {e}')
        QMessageBox.information(self,'Sauvé','CR enregistré.'); self._refresh_tables()

    def _update_word_count(self):
        wc = len(self.cr_text.toPlainText().split())
        self.lbl_wc.setText(f'Mots: {wc}')

    # ==== CR & ToDo ====
    def _build_tab_cr_todo(self):
        w=QWidget(); lay=QVBoxLayout(w)
        fl=QHBoxLayout(); fl.addWidget(QLabel('Filtre Thématique:'))
        self.f_th=QLineEdit(); self.f_th.setPlaceholderText('contient…'); self.f_th.setStyleSheet('color:black;background:white;'); fl.addWidget(self.f_th)
        fl.addWidget(QLabel('Filtre Projet:')); self.f_pr=QLineEdit(); self.f_pr.setPlaceholderText('contient…'); self.f_pr.setStyleSheet('color:black;background:white;'); fl.addWidget(self.f_pr)
        fl.addWidget(QLabel('Tri:')); self.sort_sel=QComboBox(); self.sort_sel.addItems(['date DESC','date ASC']); fl.addWidget(self.sort_sel)
        btn_apply=QPushButton('Appliquer'); btn_apply.clicked.connect(self._refresh_tables); fl.addWidget(btn_apply)
        lay.addLayout(fl)

        self.tbl_meet=QTableWidget(0,6); self.tbl_meet.setHorizontalHeaderLabels(['ID','Date','Thématique','Projet','Participants','Contenu']); self.tbl_meet.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(QLabel('Compte-rendus')); lay.addWidget(self.tbl_meet)

        self.tbl_todo=QTableWidget(0,7); self.tbl_todo.setHorizontalHeaderLabels(['ID','Meeting_ID','Thématique','Projet','Action','Acteur','Échéance']); self.tbl_todo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(QLabel('ToDo')); lay.addWidget(self.tbl_todo)

        btns=QHBoxLayout(); b_add=QPushButton('Ajouter ToDo (CR sélectionné)'); b_add.clicked.connect(self._add_todo_from_selection); b_edit=QPushButton('Modifier CR/Participants'); b_edit.clicked.connect(self._edit_meeting_from_selection); btns.addWidget(b_add); btns.addWidget(b_edit); lay.addLayout(btns)

        self.tab_cr_todo=w; self.tabs.addTab(w,'CR & ToDo'); self._refresh_tables()

    def _build_query(self):
        where=[]; args=[]
        if self.f_th.text().strip():
            where.append('thematique LIKE ?'); args.append('%'+self.f_th.text().strip()+'%')
        if self.f_pr.text().strip():
            where.append('projet LIKE ?'); args.append('%'+self.f_pr.text().strip()+'%')
        where_sql = ('WHERE '+ ' AND '.join(where)) if where else ''
        order = self.sort_sel.currentText() if hasattr(self,'sort_sel') else 'date DESC'
        sql_m = f'SELECT id,date,thematique,projet,participants,content FROM meetings {where_sql} ORDER BY {order}'
        sql_t = 'SELECT id,meeting_id,thematique,projet,action,acteur,echeance FROM todos ORDER BY id DESC'
        return sql_m, args, sql_t

    def _refresh_tables(self):
        con=db.get_conn(); cur=con.cursor()
        sql_m, args, sql_t = self._build_query()
        cur.execute(sql_m, args)
        cols_m=[d[0] for d in cur.description]; rows_m=[dict(zip(cols_m,r)) for r in cur.fetchall()]
        self.tbl_meet.setRowCount(len(rows_m))
        for i,r in enumerate(rows_m):
            for j,key in enumerate(['id','date','thematique','projet','participants','content']):
                self.tbl_meet.setItem(i,j,QTableWidgetItem(str(r.get(key,''))))

        cur.execute(sql_t)
        cols_t=[d[0] for d in cur.description]; rows_t=[dict(zip(cols_t,r)) for r in cur.fetchall()]
        self.tbl_todo.setRowCount(len(rows_t))
        for i,r in enumerate(rows_t):
            for j,key in enumerate(['id','meeting_id','thematique','projet','action','acteur','echeance']):
                item = QTableWidgetItem(str(r.get(key,'')))
                if (key=='acteur' and not r.get('acteur')) or (key=='echeance' and not r.get('echeance')):
                    item.setBackground(Qt.yellow)
                self.tbl_todo.setItem(i,j,item)
        con.close()

    def _selected_meeting_id(self):
        idx=self.tbl_meet.currentRow()
        if idx<0: return None
        return int(self.tbl_meet.item(idx,0).text())

    def _add_todo_from_selection(self):
        mid=self._selected_meeting_id()
        if not mid: _err('Sélectionne d\'abord un CR.'); return
        thematique=self.tbl_meet.item(self.tbl_meet.currentRow(),2).text() if self.tbl_meet.currentRow()>=0 else ''
        projet=self.tbl_meet.item(self.tbl_meet.currentRow(),3).text() if self.tbl_meet.currentRow()>=0 else ''
        action, ok = QInputDialog.getText(self, 'Action', 'Action:')
        if not ok: return
        acteur, ok = QInputDialog.getText(self, 'Acteur', 'Acteur:')
        if not ok: return
        echeance, ok = QInputDialog.getText(self, 'Échéance', 'Échéance (YYYY-MM-DD):')
        if not ok: return
        con=db.get_conn(); cur=con.cursor(); cur.execute('INSERT INTO todos(meeting_id,thematique,projet,action,acteur,echeance) VALUES (?,?,?,?,?,?)',(mid,thematique,projet,action,acteur,echeance)); con.commit(); con.close(); self._refresh_tables()

    def _edit_meeting_from_selection(self):
        idx=self.tbl_meet.currentRow()
        if idx<0: _err('Sélectionne d\'abord un CR.'); return
        mid=int(self.tbl_meet.item(idx,0).text()); date=self.tbl_meet.item(idx,1).text(); participants=self.tbl_meet.item(idx,4).text(); content=self.tbl_meet.item(idx,5).text()
        text=QTextEdit(); text.setPlainText(content); part=QLineEdit(participants); part.setStyleSheet('color:black;background:white;')
        dlg=QWidget(); dlg.setWindowTitle('Édition du CR'); v=QVBoxLayout(dlg); v.addWidget(QLabel(f'CR #{mid} - {date}')); v.addWidget(QLabel('Participants')); v.addWidget(part); v.addWidget(QLabel('Contenu')); v.addWidget(text)
        btn=QPushButton('Enregistrer'); v.addWidget(btn)
        def _save():
            con=db.get_conn(); cur=con.cursor(); cur.execute('UPDATE meetings SET participants=?, content=? WHERE id=?',(part.text(), text.toPlainText(), mid)); con.commit(); con.close(); dlg.close(); self._refresh_tables()
        btn.clicked.connect(_save); dlg.resize(600,400); dlg.show()

    # ==== EXPORT ====
    def _build_tab_export(self):
        w=QWidget(); lay=QVBoxLayout(w); btn=QPushButton('Export : Excel (CR, ToDo, ToDo_Global)'); btn.clicked.connect(self._export_excel); lay.addWidget(btn); self.tab_export=w; self.tabs.addTab(w,'Export')

    def _export_excel(self):
        out=EXPORTS_DIR/f'Export_CHAP1_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        con=db.get_conn(); cur=con.cursor()
        cols_m=['id','date','thematique','projet','participants','content']; cur.execute('SELECT id,date,thematique,projet,participants,content FROM meetings ORDER BY date DESC'); rows_m=[dict(zip(cols_m,r)) for r in cur.fetchall()]
        cols_t=['id','meeting_id','thematique','projet','action','acteur','echeance']; cur.execute('SELECT id,meeting_id,thematique,projet,action,acteur,echeance FROM todos ORDER BY id DESC'); rows_t=[dict(zip(cols_t,r)) for r in cur.fetchall()]
        con.close(); export_excel(rows_m, rows_t, out); QMessageBox.information(self,'Export',f'Fichier exporté : {out}'); open_folder(out.parent)

    # ==== PARAMS ====
    def _build_tab_params(self):
        w=QWidget(); lay=QVBoxLayout(w); lay.addWidget(QLabel('Modèles Whisper (faster-whisper)'))
        line=QHBoxLayout(); self.model_choice=QComboBox(); self.model_choice.addItems(['small','medium']); line.addWidget(self.model_choice)
        self.btn_download=QPushButton('Télécharger'); line.addWidget(self.btn_download)
        self.lbl_status=QLabel('Statut : -'); line.addWidget(self.lbl_status)
        self.btn_open_cr=QPushButton('Ouvrir dossier CR/exports'); line.addWidget(self.btn_open_cr)
        self.btn_open_logs=QPushButton('Ouvrir logs'); line.addWidget(self.btn_open_logs)
        lay.addLayout(line)
        self.btn_download.clicked.connect(self._download_model); self.btn_open_cr.clicked.connect(lambda: open_folder(DATA_DIR)); self.btn_open_logs.clicked.connect(lambda: open_folder(LOGS_DIR))
        self.tab_params=w; self.tabs.addTab(w,'Paramètres')

    def _refresh_status_tab(self):
        sm=self.model_mgr.status('small'); md=self.model_mgr.status('medium')
        def s(st): 
            if st.downloading: return f"Téléchargement {int(st.progress*100)}% ({st.size_on_disk_mb:.0f} MB)"
            return f"{'OK' if st.present else 'Absent'} ({st.size_on_disk_mb:.0f} MB)"
        txt=f"Small: {s(sm)} | Medium: {s(md)}"
        self.lbl_status.setText(txt)

    def _download_model(self):
        name=self.model_choice.currentText(); self.model_mgr.download(name)

    def _persist_presets(self):
        try:
            if self.model_sel.currentText()=='small':
                db.set_setting('small_window', self.window_s.text().strip())
                db.set_setting('small_pas', self.pas_s.text().strip())
            else:
                db.set_setting('medium_window', self.window_s.text().strip())
                db.set_setting('medium_pas', self.pas_s.text().strip())
        except Exception as e:
            log.error(f'Preset save error: {e}')

def main():
    app=QApplication(sys.argv); win=MainWindow()
    win.window_s.editingFinished.connect(win._persist_presets)
    win.pas_s.editingFinished.connect(win._persist_presets)
    win.show(); sys.exit(app.exec_())
