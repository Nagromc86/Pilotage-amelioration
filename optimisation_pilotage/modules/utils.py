import sqlite3, datetime as dt
from pathlib import Path
APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = APP_DIR / "data" / "meetings.sqlite"
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
def now_ts(): return dt.datetime.now().isoformat(timespec="seconds")
def slugify(text): return "".join(c if c.isalnum() or c in ("-","_") else "_" for c in text.strip().replace(" ", "_"))
def save_text_to_file(text, path): Path(path).write_text(text or "", encoding="utf-8")
def read_text_file(path):
    try: return Path(path).read_text(encoding="utf-8")
    except Exception: return ""
