import sys, datetime
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt
from .modules import db
from .modules.utils import DATA_DIR, EXPORTS_DIR, MODELS_DIR, open_folder
from .modules.models_manager import ModelsManager
from .modules.audio_mix import MixerRecorder
from .modules.whisper_transcribe import transcribe_file
from .modules.export import export_excel

def _err(msg):
    QMessageBox.critical(None, 'Erreur', msg)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__(); db.init_db()
        self.setWindowTitle('CHAP1 — Compte-rendus Harmonisés et Assistance au Pilotage 1'); self.resize(1080,720)
        self.tabs=QTabWidget();
        self._build_tab_live(); self._build_tab_cr_todo(); self._build_tab_export(); self._build_tab_params()
        lay=QVBoxLayout(self); lay.addWidget(self.tabs)
        self.recorder=MixerRecorder(); self.model_mgr=ModelsManager(on_change=self._refresh_status_tab)

    def _build_tab_live(self):
        w=QWidget(); lay=QVBoxLayout(w)
        l1=QHBoxLayout(); l1.addWidget(QLabel('Modèle:'))
        self.model_sel=QComboBox(); self.model_sel.addItems(['small','medium']); self.model_sel.currentTextChanged.connect(self._on_model_change); l1.addWidget(self.model_sel)
        l1.addWidget(QLabel('Fenêtre audio (s):')); self.window_s=QLineEdit('20'); self.window_s.setMaximumWidth(100); self.window_s.setStyleSheet('color:black;background:white;'); l1.addWidget(self.window_s)
        l1.addWidget(QLabel('Pas (s):')); self.pas_s=QLineEdit('5'); self.pas_s.setMaximumWidth(100); self.pas_s.setStyleSheet('color:black;background:white;'); l1.addWidget(self.pas_s)
        l1.addWidget(QLabel('Date:')); self.date_edit=QLineEdit(datetime.date.today().isoformat()); self.date_edit.setMaximumWidth(140); self.date_edit.setStyleSheet('color:black;background:white;'); l1.addWidget(self.date_edit)
        lay.addLayout(l1)
        l2=QHBoxLayout(); self.btn_start=QPushButton('Démarrer (mix micro + système)'); self.btn_stop=QPushButton('Arrêter'); self.btn_trans=QPushButton('Transcrire')
        [l2.addWidget(b) for b in (self.btn_start,self.btn_stop,self.btn_trans)]; lay.addLayout(l2)
        self.btn_start.clicked.connect(self._start_mix); self.btn_stop.clicked.connect(self._stop_mix); self.btn_trans.clicked.connect(self._transcribe_last)
        self.cr_text=QTextEdit(); lay.addWidget(self.cr_text)
        l3=QHBoxLayout(); self.thematique_in=QLineEdit(); self.thematique_in.setPlaceholderText('Thématique'); self.projet_in=QLineEdit(); self.projet_in.setPlaceholderText('Projet'); self.participants_in=QLineEdit(); self.participants_in.setPlaceholderText('Participants (;)')
        [w.setStyleSheet('color:black;background:white;') for w in (self.thematique_in,self.projet_in,self.participants_in)]
        self.btn_save_meeting=QPushButton('Enregistrer le CR'); self.btn_save_meeting.clicked.connect(self._save_meeting)
        for it in (QLabel('Thématique:'), self.thematique_in, QLabel('Projet:'), self.projet_in, QLabel('Participants:'), self.participants_in, self.btn_save_meeting): l3.addWidget(it)
        lay.addLayout(l3)
        self.tab_live=w; self.tabs.addTab(w,'Live (Mix)'); self._on_model_change(self.model_sel.currentText())

    def _on_model_change(self,name):
        if name=='small': self.window_s.setText('12'); self.pas_s.setText('3')
        else: self.window_s.setText('24'); self.pas_s.setText('6')

    def _start_mix(self):
        out=DATA_DIR/f"live_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        try:
            self.recorder.start(out); QMessageBox.information(self,'Enregistrement',f'Enregistrement en cours → {out}')
        except Exception as e: _err(f"Impossible de démarrer l'enregistrement: {e}")

    def _stop_mix(self):
        try:
            path=self.recorder.stop(); QMessageBox.information(self,'Arrêt',f'Enregistrement sauvegardé: {path}'); self._last_wav=path
        except Exception as e: _err(f'Erreur à l\'arrêt: {e}')

    def _transcribe_last(self):
        if not hasattr(self,'_last_wav'): _err('Aucun enregistrement trouvé.'); return
        model=self.model_sel.currentText()
        try:
            txt,info=transcribe_file(self._last_wav, model_size=model); self.cr_text.setPlainText(txt)
        except Exception as e: _err(f'Transcription impossible: {e}')

    def _save_meeting(self):
        date=self.date_edit.text().strip(); the=self.thematique_in.text().strip(); prj=self.projet_in.text().strip(); part=self.participants_in.text().strip(); content=self.cr_text.toPlainText()
        con=db.get_conn(); cur=con.cursor(); cur.execute('INSERT INTO meetings(date,thematique,projet,participants,content) VALUES (?,?,?,?,?)',(date,the,prj,part,content)); con.commit(); con.close(); QMessageBox.information(self,'Sauvé','CR enregistré.'); self._refresh_tables()

    def _build_tab_cr_todo(self):
        w=QWidget(); lay=QVBoxLayout(w)
        self.tbl_meet=QTableWidget(0,6); self.tbl_meet.setHorizontalHeaderLabels(['ID','Date','Thématique','Projet','Participants','Contenu']); self.tbl_meet.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(QLabel('Compte-rendus')); lay.addWidget(self.tbl_meet)
        self.tbl_todo=QTableWidget(0,7); self.tbl_todo.setHorizontalHeaderLabels(['ID','Meeting_ID','Thématique','Projet','Action','Acteur','Échéance']); self.tbl_todo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(QLabel('ToDo')); lay.addWidget(self.tbl_todo)
        btns=QHBoxLayout(); b_add=QPushButton('Ajouter ToDo à partir du CR sélectionné'); b_add.clicked.connect(self._add_todo_from_selection); b_edit=QPushButton('Modifier CR/Participants'); b_edit.clicked.connect(self._edit_meeting_from_selection); btns.addWidget(b_add); btns.addWidget(b_edit); lay.addLayout(btns)
        self.tab_cr_todo=w; self.tabs.addTab(w,'CR & ToDo'); self._refresh_tables()

    def _refresh_tables(self):
        con=db.get_conn(); cur=con.cursor()
        rows=[dict(zip([c[0] for c in cur.description], r)) for r in cur.execute('SELECT id,date,thematique,projet,participants,content FROM meetings ORDER BY date DESC').fetchall()]
        self.tbl_meet.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,key in enumerate(['id','date','thematique','projet','participants','content']): self.tbl_meet.setItem(i,j,QTableWidgetItem(str(r.get(key,''))))
        rows_t=[dict(zip([c[0] for c in cur.description], r)) for r in cur.execute('SELECT id,meeting_id,thematique,projet,action,acteur,echeance FROM todos ORDER BY id DESC').fetchall()]
        self.tbl_todo.setRowCount(len(rows_t))
        for i,r in enumerate(rows_t):
            for j,key in enumerate(['id','meeting_id','thematique','projet','action','acteur','echeance']): self.tbl_todo.setItem(i,j,QTableWidgetItem(str(r.get(key,''))))
        con.close()

    def _selected_meeting_id(self):
        idx=self.tbl_meet.currentRow();
        if idx<0: return None
        return int(self.tbl_meet.item(idx,0).text())

    def _add_todo_from_selection(self):
        mid=self._selected_meeting_id()
        if not mid: _err('Sélectionne d\'abord un CR.'); return
        thematique=self.tbl_meet.item(self.tbl_meet.currentRow(),2).text() if self.tbl_meet.currentRow()>=0 else ''
        projet=self.tbl_meet.item(self.tbl_meet.currentRow(),3).text() if self.tbl_meet.currentRow()>=0 else ''
        action, ok = QFileDialog.getSaveFileName(self,'Saisir Action (utilise le nom de fichier comme texte)','', 'Texte (*.txt)')
        if ok and action: action=Path(action).stem
        acteur, ok2 = QFileDialog.getSaveFileName(self,'Saisir Acteur','','Texte (*.txt)')
        if ok2 and acteur: acteur=Path(acteur).stem
        echeance, ok3 = QFileDialog.getSaveFileName(self,'Saisir Échéance (YYYY-MM-DD)','','Texte (*.txt)')
        if ok3 and echeance: echeance=Path(echeance).stem
        con=db.get_conn(); cur=con.cursor(); cur.execute('INSERT INTO todos(meeting_id,thematique,projet,action,acteur,echeance) VALUES (?,?,?,?,?,?)',(mid,thematique,projet,action,acteur,echeance)); con.commit(); con.close(); self._refresh_tables()

    def _edit_meeting_from_selection(self):
        idx=self.tbl_meet.currentRow();
        if idx<0: _err('Sélectionne d\'abord un CR.'); return
        mid=int(self.tbl_meet.item(idx,0).text()); date=self.tbl_meet.item(idx,1).text(); participants=self.tbl_meet.item(idx,4).text(); content=self.tbl_meet.item(idx,5).text()
        text=QTextEdit(); text.setPlainText(content); part=QLineEdit(participants); part.setStyleSheet('color:black;background:white;')
        dlg=QWidget(); dlg.setWindowTitle('Édition du CR'); v=QVBoxLayout(dlg); v.addWidget(QLabel(f'CR #{mid} - {date}')); v.addWidget(QLabel('Participants')); v.addWidget(part); v.addWidget(QLabel('Contenu')); v.addWidget(text)
        btn=QPushButton('Enregistrer'); v.addWidget(btn)
        def _save():
            con=db.get_conn(); cur=con.cursor(); cur.execute('UPDATE meetings SET participants=?, content=? WHERE id=?',(part.text(), text.toPlainText(), mid)); con.commit(); con.close(); dlg.close(); self._refresh_tables()
        btn.clicked.connect(_save); dlg.resize(600,400); dlg.show()

    def _build_tab_export(self):
        w=QWidget(); lay=QVBoxLayout(w); btn=QPushButton('Export : Excel (CR, ToDo, ToDo_Global)'); btn.clicked.connect(self._export_excel); lay.addWidget(btn); self.tab_export=w; self.tabs.addTab(w,'Export')

    def _export_excel(self):
        out=EXPORTS_DIR/f'Export_CHAP1_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx'
        con=db.get_conn(); cur=con.cursor()
        cols_m=['id','date','thematique','projet','participants','content']; rows_m=[dict(zip(cols_m,r)) for r in cur.execute('SELECT id,date,thematique,projet,participants,content FROM meetings ORDER BY date DESC').fetchall()]
        cols_t=['id','meeting_id','thematique','projet','action','acteur','echeance']; rows_t=[dict(zip(cols_t,r)) for r in cur.execute('SELECT id,meeting_id,thematique,projet,action,acteur,echeance FROM todos ORDER BY id DESC').fetchall()]
        con.close(); export_excel(rows_m, rows_t, out); QMessageBox.information(self,'Export',f'Fichier exporté : {out}'); open_folder(out.parent)

    def _build_tab_params(self):
        w=QWidget(); lay=QVBoxLayout(w); lay.addWidget(QLabel('Modèles Whisper (faster-whisper)'))
        line=QHBoxLayout(); self.model_choice=QComboBox(); self.model_choice.addItems(['small','medium']); line.addWidget(self.model_choice)
        self.btn_download=QPushButton('Télécharger'); line.addWidget(self.btn_download)
        self.lbl_status=QLabel('Statut : -'); line.addWidget(self.lbl_status)
        self.btn_open=QPushButton('Ouvrir dossier CR/exports'); line.addWidget(self.btn_open); lay.addLayout(line)
        self.btn_download.clicked.connect(self._download_model); self.btn_open.clicked.connect(lambda: open_folder(DATA_DIR))
        self.tab_params=w; self.tabs.addTab(w,'Paramètres')

    def _refresh_status_tab(self):
        sm=self.model_mgr.status('small'); md=self.model_mgr.status('medium')
        txt=f"Small: {'OK' if sm.present else 'Absent'} ({sm.size_on_disk_mb:.0f} MB) | Medium: {'OK' if md.present else 'Absent'} ({md.size_on_disk_mb:.0f} MB)";
        if sm.downloading or md.downloading: txt+=' | Téléchargement en cours…'
        self.lbl_status.setText(txt)

    def _download_model(self):
        name=self.model_choice.currentText(); self.model_mgr.download(name)

def main():
    app=QApplication(sys.argv); win=MainWindow(); win.show(); sys.exit(app.exec_())
