
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading, time, os, subprocess, sys
from pathlib import Path
import sounddevice as sd
from .modules import db, utils, models_manager, whisper_transcribe as wt, audio_mix, export as export_mod

class AppState:
    def __init__(self):
        self.transcript=''; self.current_meeting_id=None; self.word_count=0; self.chunks=0
        self.autosave_path = utils.AUTOSAVE_DIR / 'live_autosave.txt'

class MainWindow:
    def __init__(self, root):
        self.root=root; db.init_db()
        self.model_mgr = models_manager.ModelsManager(on_change=None)
        root.title('CHAP1 – Compte-rendus Harmonises et Assistance au Pilotage 1 (v2.4.6)'); root.geometry('1150x780')
        self._build_ui();
        self.model_mgr.on_change = self._on_model_change
        self.model_mgr.refresh()
        self._start_autosave()

    def _build_ui(self):
        self.nb=ttk.Notebook(self.root); self.nb.pack(fill='both', expand=True)
        self.tab_live=ttk.Frame(self.nb); self.tab_cr=ttk.Frame(self.nb); self.tab_export=ttk.Frame(self.nb); self.tab_settings=ttk.Frame(self.nb)
        self.nb.add(self.tab_live, text='Live (Mix)'); self.nb.add(self.tab_cr, text='CR & ToDo'); self.nb.add(self.tab_export, text='Export'); self.nb.add(self.tab_settings, text='Paramètres')
        self._build_tab_live(); self._build_tab_cr(); self._build_tab_export(); self._build_tab_settings()
        self.root.bind('<Control-r>', lambda e: self._toggle_live()); self.root.bind('<Control-s>', lambda e: self._save_cr())

    def _build_tab_live(self):
        frm=ttk.Frame(self.tab_live); frm.pack(fill='both', expand=True, padx=12, pady=12)
        top=ttk.Frame(frm); top.pack(fill='x', pady=6)
        ttk.Label(top, text='Thématique:').pack(side='left'); self.ent_thematique=ttk.Entry(top, width=22); self.ent_thematique.pack(side='left', padx=6)
        ttk.Label(top, text='Projet:').pack(side='left', padx=(16,0)); self.ent_projet=ttk.Entry(top, width=22); self.ent_projet.pack(side='left', padx=6)
        ttk.Label(top, text='Titre:').pack(side='left', padx=(16,0)); self.ent_title=ttk.Entry(top, width=30); self.ent_title.pack(side='left', padx=6)
        ttk.Label(top, text='Date:').pack(side='left', padx=(16,0)); self.ent_date=ttk.Entry(top, width=12); self.ent_date.insert(0, utils.today_str()); self.ent_date.pack(side='left', padx=6)

        mid=ttk.Frame(frm); mid.pack(fill='x', pady=6)
        ttk.Label(mid, text='Modèle:').pack(side='left'); self.cbo_model=ttk.Combobox(mid, values=['small','medium'], width=10, state='readonly'); self.cbo_model.current(0); self.cbo_model.pack(side='left', padx=6)
        ttk.Label(mid, text='Pas (s):').pack(side='left', padx=(16,0)); self.spn_chunk=tk.Spinbox(mid, from_=6, to=60, width=6); self.spn_chunk.delete(0,'end'); self.spn_chunk.insert(0,'15'); self.spn_chunk.pack(side='left', padx=6)
        ttk.Label(mid, text='Micro (entrée):').pack(side='left', padx=(16,0)); self.cbo_mic=ttk.Combobox(mid, width=40); self.cbo_mic.pack(side='left', padx=6)
        ttk.Label(mid, text='Système (sortie, loopback):').pack(side='left', padx=(16,0)); self.cbo_sys=ttk.Combobox(mid, width=40); self.cbo_sys.pack(side='left', padx=6)
        self.btn_toggle=ttk.Button(mid, text='Démarrer (mix micro + système)', command=self._toggle_live); self.btn_toggle.pack(side='left', padx=16)

        stat=ttk.Frame(frm); stat.pack(fill='x', pady=6)
        self.var_status=tk.StringVar(value='Prêt.'); ttk.Label(stat, textvariable=self.var_status).pack(side='left')
        self.var_wc=tk.StringVar(value='Mots: 0'); ttk.Label(stat, textvariable=self.var_wc).pack(side='right')
        self.var_chunks=tk.StringVar(value='Chunks: 0'); ttk.Label(stat, textvariable=self.var_chunks).pack(side='right', padx=(0,16))

        self.txt=tk.Text(frm, wrap='word', height=22); self.txt.pack(fill='both', expand=True, pady=(6,0))

        self._fill_devices(); self._on_model_size()
        self.cbo_model.bind('<<ComboboxSelected>>', lambda e: self._on_model_size())

    def _build_tab_cr(self):
        frm=ttk.Frame(self.tab_cr); frm.pack(fill='both', expand=True, padx=12, pady=12)
        filt=ttk.Frame(frm); filt.pack(fill='x')
        ttk.Label(filt, text='Filtre Thématique:').pack(side='left'); self.f_them=ttk.Entry(filt, width=20); self.f_them.pack(side='left', padx=6)
        ttk.Label(filt, text='Projet:').pack(side='left'); self.f_proj=ttk.Entry(filt, width=20); self.f_proj.pack(side='left', padx=6)
        ttk.Button(filt, text='Appliquer', command=self._refresh_tables).pack(side='left', padx=12)

        cols_cr=('id','date','thematique','projet','title','participants')
        self.tree_cr=ttk.Treeview(frm, columns=cols_cr, show='headings', height=8)
        for c in cols_cr:
            self.tree_cr.heading(c, text=c.capitalize())
            self.tree_cr.column(c, width=140 if c!='title' else 240)
        self.tree_cr.pack(fill='x', pady=8)

        btns=ttk.Frame(frm); btns.pack(fill='x', pady=4)
        ttk.Button(btns, text='Éditer participants', command=self._edit_participants).pack(side='left', padx=4)
        ttk.Button(btns, text='Éditer CR', command=self._edit_cr).pack(side='left', padx=4)

        cols_td=('id','meeting_id','thematique','projet','action','acteur','echeance','status')
        self.tree_td=ttk.Treeview(frm, columns=cols_td, show='headings', height=8)
        for c in cols_td:
            self.tree_td.heading(c, text=c.capitalize())
            self.tree_td.column(c, width=120 if c not in ('action',) else 320)
        self.tree_td.pack(fill='both', expand=True)
        self._refresh_tables()

    def _build_tab_export(self):
        frm=ttk.Frame(self.tab_export); frm.pack(fill='x', padx=12, pady=12)
        ttk.Button(frm, text='Exporter Excel (CR, ToDo, ToDo_Global)', command=self._do_export).pack(side='left')

    def _build_tab_settings(self):
        frm=ttk.Frame(self.tab_settings); frm.pack(fill='both', expand=True, padx=12, pady=12)
        box=ttk.LabelFrame(frm, text='Modèles Whisper (faster-whisper)'); box.pack(fill='x', pady=8)
        self.pb_small=ttk.Progressbar(box, orient='horizontal', mode='determinate', maximum=100)
        self.pb_medium=ttk.Progressbar(box, orient='horizontal', mode='determinate', maximum=100)
        self.lbl_small=ttk.Label(box, text='small: état inconnu'); self.lbl_medium=ttk.Label(box, text='medium: état inconnu')
        row1=ttk.Frame(box); row1.pack(fill='x', padx=8, pady=4)
        ttk.Button(row1, text='Télécharger small', command=lambda: self._download_model('small')).pack(side='left')
        self.lbl_small.pack(fill='x', padx=8); self.pb_small.pack(fill='x', padx=8, pady=(0,6))
        row2=ttk.Frame(box); row2.pack(fill='x', padx=8, pady=4)
        ttk.Button(row2, text='Télécharger medium', command=lambda: self._download_model('medium')).pack(side='left')
        self.lbl_medium.pack(fill='x', padx=8); self.pb_medium.pack(fill='x', padx=8, pady=(0,6))

        fold=ttk.LabelFrame(frm, text='Dossiers'); fold.pack(fill='x', pady=8)
        ttk.Label(fold, text=f'Données: {utils.DATA_DIR}').pack(anchor='w', padx=8, pady=2)
        ttk.Label(fold, text=f'Exports: {utils.EXPORTS_DIR}').pack(anchor='w', padx=8, pady=2)
        ttk.Label(fold, text=f'Logs: {utils.LOGS_DIR}').pack(anchor='w', padx=8, pady=2)
        ttk.Button(fold, text='Ouvrir logs', command=lambda: self._open_folder(utils.LOGS_DIR)).pack(anchor='w', padx=8, pady=6)

        self._on_model_change()

    def _open_folder(self, p: Path):
        try:
            if os.name == 'nt': os.startfile(p)  # type: ignore
            elif sys.platform == 'darwin': subprocess.Popen(['open', str(p)])
            else: subprocess.Popen(['xdg-open', str(p)])
        except Exception as e:
            messagebox.showerror('Erreur', str(e))

    def _fill_devices(self):
        try:
            devs=audio_mix.LiveMixer.list_devices()
            names=[f"{i}: {d['name']}" for i,d in enumerate(devs)]
            self.cbo_mic['values']=names; self.cbo_sys['values']=names
            try:
                in_idx, out_idx = sd.default.device
                if isinstance(in_idx, int) and 0 <= in_idx < len(devs): self.cbo_mic.set(f"{in_idx}: {devs[in_idx]['name']} (Défaut)")
                if isinstance(out_idx, int) and 0 <= out_idx < len(devs): self.cbo_sys.set(f"{out_idx}: {devs[out_idx]['name']} (Défaut)")
            except Exception:
                pass
        except Exception:
            self.cbo_mic['values']=[]; self.cbo_sys['values']=[]

    def _on_model_size(self):
        size=self.cbo_model.get()
        self.spn_chunk.delete(0,'end'); self.spn_chunk.insert(0, '15' if size=='small' else '24')

    def _toggle_live(self):
        if getattr(self,'_live_on',False): self._stop_live()
        else: self._start_live()

    def _start_live(self):
        try:
            size=self.cbo_model.get(); chunk=int(self.spn_chunk.get())
            thematique=self.ent_thematique.get().strip(); projet=self.ent_projet.get().strip()
            title=self.ent_title.get().strip() or 'SansTitre'; d=self.ent_date.get().strip() or utils.today_str()
            fname="{}_{}_{}_{}.txt".format(d, utils.safe_filename(thematique), utils.safe_filename(projet), utils.safe_filename(title))
            self.current_cr_path = utils.DATA_DIR / fname
            ms=self.model_mgr.medium if size=='medium' else self.model_mgr.small
            if not ms.present: messagebox.showwarning('Modèle manquant', 'Modèle {} non installé. Téléchargez-le dans Paramètres.'.format(size)); return
            self.transcriber=wt.Transcriber(utils.MODELS_DIR, size=size)

            def parse_idx(s):
                try:
                    idx = s.split(':')[0].strip()
                    return int(idx) if idx.lstrip('-').isdigit() else None
                except Exception: return None
            mic=self.cbo_mic.get(); sysd=self.cbo_sys.get()
            mic_idx=parse_idx(mic); sys_idx=parse_idx(sysd)
            if mic_idx is None and sys_idx is None:
                messagebox.showinfo('Périphériques requis', 'Sélectionnez au moins un périphérique (micro ou système).'); return

            self.state=AppState(); self.txt.delete('1.0','end'); self.var_status.set('Enregistrement… (pas {}s)'.format(chunk)); self.btn_toggle.configure(text='Arrêter'); self._live_on=True
            def on_chunk(path: Path):
                try:
                    text=self.transcriber.transcribe_wav(path)
                    if text:
                        self.state.transcript += (' ' + text if self.state.transcript else text)
                        self.state.word_count = len(self.state.transcript.split()); self.state.chunks += 1
                        self.txt.insert('end', ' ' + text); self.txt.see('end')
                        self.var_wc.set('Mots: {}'.format(self.state.word_count)); self.var_chunks.set('Chunks: {}'.format(self.state.chunks));
                except Exception as e:
                    utils.log_exc(e)
                finally:
                    try: path.unlink(missing_ok=True)
                    except Exception: pass
            self.mixer=audio_mix.LiveMixer(chunk_seconds=chunk, mic_device=mic_idx, sys_device=sys_idx, on_chunk=on_chunk, out_dir=utils.AUTOSAVE_DIR); self.mixer.start()
        except Exception as e:
            messagebox.showerror('Erreur', str(e)); utils.log_exc(e)

    def _stop_live(self):
        try:
            if hasattr(self,'mixer') and self.mixer: self.mixer.stop()
        except Exception as e:
            utils.log_exc(e)
        self._live_on=False; self.btn_toggle.configure(text='Démarrer (mix micro + système)'); self.var_status.set('Arrêté.')
        thematique=self.ent_thematique.get().strip(); projet=self.ent_projet.get().strip()
        title=self.ent_title.get().strip() or 'SansTitre'; d=self.ent_date.get().strip() or utils.today_str()
        db.add_meeting(d, thematique, projet, title, '', getattr(self.state,'transcript',''), '') ; self._refresh_tables()

    def _save_cr(self):
        if not hasattr(self,'current_cr_path'): self.current_cr_path = utils.DATA_DIR / '{}_CR.txt'.format(utils.today_str())
        self.current_cr_path.write_text(self.txt.get('1.0','end').strip(), encoding='utf-8'); messagebox.showinfo('Sauvegarde', 'CR enregistré : {}'.format(self.current_cr_path))

    def _status_str(self, ms): return '{} ({}%)'.format(ms.status_text, ms.progress)

    def _on_model_change(self):
        if not hasattr(self,'pb_small'): return
        s=self.model_mgr.small; m=self.model_mgr.medium
        self.lbl_small.config(text='small: '+self._status_str(s)); self.pb_small['value']=s.progress
        self.lbl_medium.config(text='medium: '+self._status_str(m)); self.pb_medium['value']=m.progress

    def _download_model(self, size): self.model_mgr.download(size); self._on_model_change()

    def _get_selected_meeting_id(self):
        sel=self.tree_cr.selection()
        if not sel: messagebox.showinfo('Sélection requise','Sélectionnez un compte-rendu.'); return None
        vals=self.tree_cr.item(sel[0],'values')
        if not vals: return None
        try: return int(vals[0])
        except Exception: return None

    def _edit_participants(self):
        mid=self._get_selected_meeting_id()
        if not mid: return
        row=db.get_meeting(mid)
        if not row: messagebox.showerror('Erreur','Réunion introuvable.'); return
        top=tk.Toplevel(self.root); top.title('Éditer participants'); top.geometry('420x160'); top.transient(self.root)
        ttk.Label(top, text='Participants (séparés par ; )').pack(anchor='w', padx=12, pady=(10,4))
        ent=tk.Entry(top); ent.pack(fill='x', padx=12); ent.insert(0, row[5] or '')
        btns=ttk.Frame(top); btns.pack(fill='x', pady=12)
        def save():
            db.update_meeting(mid, participants=ent.get().strip())
            top.destroy(); self._refresh_tables()
        ttk.Button(btns, text='Enregistrer', command=save).pack(side='right', padx=8)
        ttk.Button(btns, text='Annuler', command=top.destroy).pack(side='right')

    def _edit_cr(self):
        mid=self._get_selected_meeting_id()
        if not mid: return
        row=db.get_meeting(mid)
        if not row: messagebox.showerror('Erreur','Réunion introuvable.'); return
        top=tk.Toplevel(self.root); top.title('Éditer CR'); top.geometry('800x500'); top.transient(self.root)
        txt=tk.Text(top, wrap='word'); txt.pack(fill='both', expand=True, padx=8, pady=8); txt.insert('1.0', row[6] or '')
        btns=ttk.Frame(top); btns.pack(fill='x', pady=8)
        def save():
            db.update_meeting(mid, content=txt.get('1.0','end').strip())
            top.destroy(); self._refresh_tables()
        ttk.Button(btns, text='Enregistrer', command=save).pack(side='right', padx=8)
        ttk.Button(btns, text='Annuler', command=top.destroy).pack(side='right')

    def _refresh_tables(self):
        for tr in (self.tree_cr,self.tree_td):
            for i in tr.get_children(): tr.delete(i)
        filters={}
        if hasattr(self,'f_them') and self.f_them.get().strip(): filters['thematique']=self.f_them.get().strip()
        if hasattr(self,'f_proj') and self.f_proj.get().strip(): filters['projet']=self.f_proj.get().strip()
        meetings=db.list_meetings(filters=filters)
        for row in meetings:
            self.tree_cr.insert('', 'end', values=row[:6])
        todos=db.list_todos()
        for row in todos:
            tag = 'warn' if (not row[6]) or (not row[5]) else ''
            iid=self.tree_td.insert('', 'end', values=row, tags=(tag,))
            if tag: self.tree_td.tag_configure('warn', background='#FFF0F0')

    def _do_export(self):
        path=filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel','*.xlsx')], initialfile='CHAP1_export.xlsx')
        if not path: return
        meetings=db.list_meetings(); todos=db.list_todos()
        try:
            export_mod.export_excel(Path(path), meetings, todos)
            messagebox.showinfo('Export', 'Export OK : {}'.format(path))
        except Exception as e:
            messagebox.showerror('Export', str(e)); utils.log_exc(e)

    def _start_autosave(self):
        def loop():
            while True:
                try:
                    txt=self.txt.get('1.0','end').strip()
                    if txt:
                        utils.AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
                        self.state.autosave_path.write_text(txt, encoding='utf-8')
                except Exception as e:
                    utils.log_exc(e)
                time.sleep(30)
        threading.Thread(target=loop, daemon=True).start()

def main():
    root=tk.Tk(); MainWindow(root); root.mainloop()
