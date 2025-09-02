from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable
import threading, os
from .utils import MODELS_DIR
from huggingface_hub import snapshot_download

@dataclass
class ModelStatus:
    name: str
    present: bool
    size_on_disk_mb: float
    downloading: bool=False
    progress: float=0.0

MODEL_REPOS={'small':'guillaumekln/faster-whisper-small','medium':'guillaumekln/faster-whisper-medium'}

class ModelsManager:
    def __init__(self,on_change:Optional[Callable]=None):
        self.on_change=on_change
        self._status={k:ModelStatus(k,False,0.0) for k in MODEL_REPOS}
        self.refresh()
    def _calc_size_mb(self,p:Path)->float:
        total=0
        for root,_,files in os.walk(p):
            for f in files:
                try: total+=(Path(root)/f).stat().st_size
                except: pass
        return total/(1024*1024)
    def refresh(self):
        for k in self._status:
            local=MODELS_DIR/f'faster-whisper-{k}'
            present=local.exists() and any(local.iterdir())
            size=self._calc_size_mb(local) if present else 0.0
            st=self._status[k]; st.present=present; st.size_on_disk_mb=size; st.downloading=False; st.progress=1.0 if present else 0.0
        if self.on_change: self.on_change()
    def status(self,name:str)->'ModelStatus':
        return self._status[name]
    def download(self,name:str):
        repo=MODEL_REPOS[name]
        local_dir=MODELS_DIR/f'faster-whisper-{name}'
        local_dir.mkdir(parents=True, exist_ok=True)
        def _run():
            try:
                self._status[name].downloading=True
                if self.on_change: self.on_change()
                snapshot_download(repo_id=repo, local_dir=str(local_dir), local_dir_use_symlinks=False)
                self.refresh()
            except Exception:
                self._status[name].downloading=False
                if self.on_change: self.on_change()
        threading.Thread(target=_run,daemon=True).start()
