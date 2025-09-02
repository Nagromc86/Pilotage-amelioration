
import threading, time
from .utils import MODELS_DIR

class ModelsManager:
    def __init__(self, on_change=None):
        self.on_change = on_change
        self.model = "small"  # or "medium"
        self.progress = 0
        self.state = "not_installed"  # not_installed | downloading | installed

    def _model_path(self):
        return MODELS_DIR / f"faster-whisper-{self.model}"

    def is_installed(self):
        p = self._model_path()
        return p.exists() and any(p.iterdir())

    def refresh(self):
        self.state = "installed" if self.is_installed() else "not_installed"
        if self.on_change: self.on_change()

    def set_model(self, name):
        self.model = name
        self.refresh()

    def download(self):
        if self.state == "installed": return
        self.state = "downloading"; self.progress = 0
        if self.on_change: self.on_change()
        target = self._model_path()
        target.mkdir(parents=True, exist_ok=True)
        def run():
            for i in range(1, 101):
                time.sleep(0.03 if self.model=='small' else 0.05)
                self.progress = i
                if self.on_change: self.on_change()
            (target / "MODEL_CONTENT.bin").write_bytes(b"placeholder-model")
            self.state = "installed"
            if self.on_change: self.on_change()
        threading.Thread(target=run, daemon=True).start()
