from pathlib import Path
import os

APP_NAME = "CHAP1"
BASE_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / APP_NAME
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"
AUTOSAVE_DIR = BASE_DIR / "autosave"
for p in [DATA_DIR, EXPORTS_DIR, LOGS_DIR, AUTOSAVE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "chap1.db"

def ensure_dirs():
    for p in [DATA_DIR, EXPORTS_DIR, LOGS_DIR, AUTOSAVE_DIR]:
        p.mkdir(parents=True, exist_ok=True)