import os, sys, datetime, subprocess
from pathlib import Path

def is_frozen():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def app_root():
    if is_frozen():
        base = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'CHAP1'
        base.mkdir(parents=True, exist_ok=True)
        return base
    else:
        return Path(__file__).resolve().parents[2]

APP_DIR = app_root()
DATA_DIR = APP_DIR / 'data'
MODELS_DIR = APP_DIR / 'models'
EXPORTS_DIR = APP_DIR / 'exports'
for p in (DATA_DIR, MODELS_DIR, EXPORTS_DIR):
    p.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / 'chap1.db'
def now_ts():
    import datetime
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def open_folder(path: Path):
    try:
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', str(path)])
        else:
            subprocess.Popen(['xdg-open', str(path)])
    except Exception:
        pass
