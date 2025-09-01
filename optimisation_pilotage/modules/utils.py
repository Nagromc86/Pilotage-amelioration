
import os, sys, sqlite3
from pathlib import Path
from datetime import datetime

APP_NAME = "CHAP1"
APP_DIR = None
DATA_DIR = None
EXPORTS_DIR = None
MODELS_DIR = None
DB_PATH = None

def _base_dir():
    # Prefer user-local AppData on Windows, else home
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

def resolve_dirs():
    global APP_DIR, DATA_DIR, EXPORTS_DIR, MODELS_DIR, DB_PATH
    if getattr(sys, "_MEIPASS", None):
        # running as bundled exe
        base = _base_dir()
        APP_DIR = base
        DATA_DIR = base / "data"
        EXPORTS_DIR = base / "exports"
        MODELS_DIR = base / "models"
    else:
        # running from source
        here = Path(__file__).resolve().parent.parent
        APP_DIR = here
        DATA_DIR = here / "data"
        EXPORTS_DIR = here / "data" / "exports"
        MODELS_DIR = here / "data" / "models"
    for d in [DATA_DIR, EXPORTS_DIR, MODELS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    global DB_PATH
    DB_PATH = DATA_DIR / "chap1.db"

resolve_dirs()

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def path_for_meeting_txt(meeting_id:int):
    return DATA_DIR / f"CR_{meeting_id}.txt"
