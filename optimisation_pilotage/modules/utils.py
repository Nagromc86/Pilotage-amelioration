import os, sys, sqlite3, datetime as dt
from pathlib import Path

def _user_base_dir() -> Path:
    # Choose a per-user writable base dir
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / "Optimisation_Pilotage"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Optimisation_Pilotage"
    else:
        return Path.home() / ".optimisation_pilotage"

APP_DIR = _user_base_dir()
DATA_DIR = APP_DIR / "data"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "meetings.sqlite"

def _ensure_dirs():
    for p in [APP_DIR, DATA_DIR, EXPORTS_DIR]:
        p.mkdir(parents=True, exist_ok=True)

def get_conn():
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def now_ts():
    return dt.datetime.now().isoformat(timespec="seconds")

def slugify(text):
    return "".join(c if c.isalnum() or c in ("-","_") else "_" for c in text.strip().replace(" ", "_"))

def save_text_to_file(text, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text or "", encoding="utf-8")

def read_text_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""
