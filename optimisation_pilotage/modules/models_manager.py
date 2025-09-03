import threading
from pathlib import Path
from typing import Optional, Callable
from huggingface_hub import list_repo_files, hf_hub_download
from .utils import MODELS_DIR
MODEL_REPOS={'small':'Systran/faster-whisper-small','medium':'Systran/faster-whisper-medium'}
class ModelStatus:
    def __init__(self,name): self.name=name; self.present=False; self.progress=0; self.status_text='Non téléchargé'; self.path=None
class ModelsManager:
    def __init__(self,on_change:Optional[Callable]=None):
        self.on_change=on_change; self.small=ModelStatus('small'); self.medium=ModelStatus('medium')
    def refresh(self):
        for ms in (self.small,self.medium):
            p=MODELS_DIR/f'faster-whisper-{ms.name}'; ms.path=p; ms.present=p.exists() and any(p.iterdir()); 
            ms.progress=100 if ms.present else 0; ms.status_text='Installé' if ms.present else 'Non téléchargé'
        if self.on_change: self.on_change()
    def download(self,size):
        ms=self.small if size=='small' else self.medium
        if ms.present: ms.progress=100; ms.status_text='Installé'; self.on_change and self.on_change(); return
        def worker():
            try:
                repo=MODEL_REPOS[size]; dst=MODELS_DIR/f'faster-whisper-{size}'; dst.mkdir(parents=True, exist_ok=True)
                ms.status_text='Récupération…'; ms.progress=1; self.on_change and self.on_change()
                files=list_repo_files(repo, repo_type='model'); total=max(1,len(files)); done=0
                for f in files:
                    try: hf_hub_download(repo, f, repo_type='model', local_dir=str(dst), local_dir_use_symlinks=False)
                    except Exception: pass
                    done+=1; ms.progress=min(99,int(done*100/total)); ms.status_text=f'Téléchargement {ms.progress}%'; self.on_change and self.on_change()
                ms.progress=100; ms.status_text='Installé'
            except Exception as e:
                ms.progress=0; ms.status_text=f'Erreur: {e}'
            finally: self.refresh()
        threading.Thread(target=worker, daemon=True).start()
