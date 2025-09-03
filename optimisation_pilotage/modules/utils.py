from pathlib import Path
import os, datetime
APP_NAME = "CHAP1"
BASE_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / APP_NAME
DATA_DIR = BASE_DIR / "data"; EXPORTS_DIR = BASE_DIR / "exports"; LOGS_DIR = BASE_DIR / "logs"; AUTOSAVE_DIR = BASE_DIR / "autosave"; MODELS_DIR = BASE_DIR / "models"
for p in (DATA_DIR, EXPORTS_DIR, LOGS_DIR, AUTOSAVE_DIR, MODELS_DIR): p.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "chap1.db"
def today_str(): return datetime.date.today().isoformat()
def safe_filename(s: str) -> str:
    for ch in '<>:"/\\|?*': s = s.replace(ch, "_")
    return "_".join(part for part in s.split() if part).strip("_")