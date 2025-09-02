
import sqlite3
from .utils import DB_PATH

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def _has_column(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def init_db():
    con = get_conn()
    cur = con.cursor()
    # Create base tables if not exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );""")
    con.commit()

    # --- Migrations (idempotent) ---
    # meetings: thematique, projet, participants, content
    for coldef in [
        ('thematique','TEXT'),
        ('projet','TEXT'),
        ('participants','TEXT'),
        ('content','TEXT')
    ]:
        col, typ = coldef
        if not _has_column(cur, 'meetings', col):
            cur.execute(f"ALTER TABLE meetings ADD COLUMN {col} {typ}")

    # todos: meeting_id, thematique, projet, action, acteur, echeance
    for coldef in [
        ('meeting_id','INTEGER'),
        ('thematique','TEXT'),
        ('projet','TEXT'),
        ('action','TEXT'),
        ('acteur','TEXT'),
        ('echeance','TEXT')
    ]:
        col, typ = coldef
        if not _has_column(cur, 'todos', col):
            cur.execute(f"ALTER TABLE todos ADD COLUMN {col} {typ}")

    con.commit()
    con.close()

def set_setting(key: str, value: str):
    con = get_conn(); cur = con.cursor()
    cur.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key,value))
    con.commit(); con.close()

def get_setting(key: str, default: str = "") -> str:
    con = get_conn(); cur = con.cursor()
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone(); con.close()
    return row[0] if row and row[0] is not None else default
