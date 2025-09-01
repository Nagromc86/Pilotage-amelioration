import os, sys, sqlite3, datetime as dt, tempfile, webbrowser
from pathlib import Path

def _candidate_base_dirs():
    paths = []
    if sys.platform.startswith("win"):
        la = os.environ.get("LOCALAPPDATA")
        if la: paths.append(Path(la) / "Optimisation_Pilotage")
        ra = os.environ.get("APPDATA")
        if ra: paths.append(Path(ra) / "Optimisation_Pilotage")
        paths.append(Path.home() / "Documents" / "Optimisation_Pilotage")
    elif sys.platform == "darwin":
        paths.append(Path.home() / "Library" / "Application Support" / "Optimisation_Pilotage")
    paths.append(Path.home() / ".optimisation_pilotage")
    paths.append(Path(tempfile.gettempdir()) / "Optimisation_Pilotage")
    seen=set(); uniq=[]
    for p in paths:
        if p and str(p) not in seen:
            uniq.append(p); seen.add(str(p))
    return uniq

def _first_working_base_dir():
    errors = []
    for base in _candidate_base_dirs():
        try:
            base.mkdir(parents=True, exist_ok=True)
            test = base / "._write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return base
        except Exception as e:
            errors.append(f"{base}: {e}")
            continue
    raise RuntimeError("No writable base directory found:\n" + "\n".join(errors))

try:
    APP_DIR = _first_working_base_dir()
except Exception:
    APP_DIR = Path(tempfile.gettempdir()) / "Optimisation_Pilotage"

DATA_DIR = APP_DIR / "data"
EXPORTS_DIR = DATA_DIR / "exports"
MODELS_DIR = DATA_DIR / "models"
DB_PATH = DATA_DIR / "meetings.sqlite"

def _ensure_dirs():
    for p in [APP_DIR, DATA_DIR, EXPORTS_DIR, MODELS_DIR]:
        p.mkdir(parents=True, exist_ok=True)

def get_conn():
    global APP_DIR, DATA_DIR, EXPORTS_DIR, MODELS_DIR, DB_PATH
    _ensure_dirs()
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except Exception as e:
        try:
            tmp_base = Path(tempfile.gettempdir()) / "Optimisation_Pilotage_Fallback"
            (tmp_base / "data").mkdir(parents=True, exist_ok=True)
            APP_DIR = tmp_base
            DATA_DIR = APP_DIR / "data"
            EXPORTS_DIR = DATA_DIR / "exports"
            MODELS_DIR = DATA_DIR / "models"
            DB_PATH = DATA_DIR / "meetings.sqlite"
            EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        except Exception as e2:
            log = Path(tempfile.gettempdir()) / "optimisation_pilotage_db_error.log"
            log.write_text(f"Primary error: {e}\nFallback error: {e2}", encoding="utf-8")
            raise

def now_ts():
    return dt.datetime.now().isoformat(timespec="seconds")

def slugify(text):
    return "".join(c if c.isalnum() or c in ("-","_") else "_" for c in text.strip().replace(" ", "_"))

def save_text_to_file(text, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or "", encoding="utf-8")

def read_text_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""

def open_folder(path: Path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception:
        try:
            webbrowser.open(str(path))
        except Exception:
            pass

def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return str(Path(base) / relative)
    return str(Path(__file__).resolve().parents[2] / relative)
