
import sqlite3
from pathlib import Path
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
    con.commit()
    con.close()
