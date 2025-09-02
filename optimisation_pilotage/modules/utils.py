
import os, sys, datetime, subprocess, logging
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
LOGS_DIR = APP_DIR / 'logs'
AUTOSAVE_DIR = APP_DIR / 'autosave'
for p in (DATA_DIR, MODELS_DIR, EXPORTS_DIR, LOGS_DIR, AUTOSAVE_DIR):
    p.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / 'chap1.db'

def now_ts():
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

def get_logger():
    LOGS_DIR.mkdir(exist_ok=True, parents=True)
    log_file = LOGS_DIR / 'app.log'
    logger = logging.getLogger('chap1')
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger
