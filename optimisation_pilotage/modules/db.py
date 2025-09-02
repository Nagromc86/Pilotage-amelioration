
import sqlite3
from .utils import DB_PATH

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        thematique TEXT,
        projet TEXT,
        participants TEXT,
        content TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER,
        thematique TEXT,
        projet TEXT,
        action TEXT,
        acteur TEXT,
        echeance TEXT,
        FOREIGN KEY(meeting_id) REFERENCES meetings(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
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
