import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable
from huggingface_hub import snapshot_download

@dataclass
class ModelStatus:
    name: str
    present: bool
    path: str
    progress: int = 0
    total: int = 0
    downloading: bool = False
    error: str = ""

class ModelManager:
    def __init__(self, models_dir: Path, on_change: Optional[Callable[[], None]] = None):
        self.models_dir = models_dir
        self.on_change = on_change
        self._lock = threading.Lock()
        self.status_small = self._build_status("faster-whisper-small")
        self.status_medium = self._build_status("faster-whisper-medium")
        self._dl_thread = None

    def _build_status(self, name: str):
        p = self.models_dir / name
        present = p.exists() and any(p.iterdir())
        return ModelStatus(name=name, present=present, path=str(p))

    def refresh(self):
        # no on_change here to avoid recursion with UI
        with self._lock:
            self.status_small = self._build_status("faster-whisper-small")
            self.status_medium = self._build_status("faster-whisper-medium")

    def _download(self, repo_id: str, local_name: str):
        st = self.status_small if "small" in local_name else self.status_medium
        with self._lock:
            st.downloading = True
            st.error = ""
            st.progress = 0
            st.total = 0
        if self.on_change: self.on_change()
        try:
            local_dir = str(self.models_dir / local_name)
            snapshot_download(repo_id=repo_id, local_dir=local_dir, local_dir_use_symlinks=False, ignore_patterns=["*.onnx*"])
            with self._lock:
                st.present = True
                st.downloading = False
                st.progress = 100
                st.total = 100
        except Exception as e:
            with self._lock:
                st.error = str(e)
                st.downloading = False
        if self.on_change: self.on_change()

    def download_small(self):
        if self._dl_thread and self._dl_thread.is_alive(): return
        self._dl_thread = threading.Thread(target=self._download, args=("Systran/faster-whisper-small", "faster-whisper-small"), daemon=True)
        self._dl_thread.start()

    def download_medium(self):
        if self._dl_thread and self._dl_thread.is_alive(): return
        self._dl_thread = threading.Thread(target=self._download, args=("Systran/faster-whisper-medium", "faster-whisper-medium"), daemon=True)
        self._dl_thread.start()
