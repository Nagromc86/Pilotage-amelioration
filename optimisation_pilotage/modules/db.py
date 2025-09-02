import sqlite3
from .utils import DB_PATH, ensure_dirs

def get_conn():
    ensure_dirs()
    return sqlite3.connect(DB_PATH)

def _has_column(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def init_db():
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    con.commit()

    for col, typ in [('thematique','TEXT'),('projet','TEXT'),('participants','TEXT'),('content','TEXT')]:
        if not _has_column(cur, 'meetings', col):
            cur.execute(f"ALTER TABLE meetings ADD COLUMN {col} {typ}")

    for col, typ in [('meeting_id','INTEGER'),('thematique','TEXT'),('projet','TEXT'),('action','TEXT'),('acteur','TEXT'),('echeance','TEXT')]:
        if not _has_column(cur, 'todos', col):
            cur.execute(f"ALTER TABLE todos ADD COLUMN {col} {typ}")

    con.commit()
    con.close()