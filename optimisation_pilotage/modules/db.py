from .utils import get_conn, now_ts

SCHEMA = """
CREATE TABLE IF NOT EXISTS themes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  theme_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  UNIQUE(theme_id, name),
  FOREIGN KEY(theme_id) REFERENCES themes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS meetings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  theme_id INTEGER NOT NULL,
  project_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  date TEXT NOT NULL,
  participants TEXT,
  source TEXT,
  transcript_path TEXT,
  summary TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(theme_id) REFERENCES themes(id) ON DELETE CASCADE,
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  meeting_id INTEGER NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS todos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  theme_id INTEGER NOT NULL,
  project_id INTEGER NOT NULL,
  meeting_id INTEGER,
  action TEXT NOT NULL,
  actor TEXT,
  due_date TEXT,
  status TEXT DEFAULT 'Ouvert',
  created_at TEXT NOT NULL,
  FOREIGN KEY(theme_id) REFERENCES themes(id) ON DELETE CASCADE,
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""

def init_db():
    conn = get_conn()
    with conn:
        for stmt in SCHEMA.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)

def list_themes():
    conn = get_conn()
    return conn.execute("SELECT id, name FROM themes ORDER BY name").fetchall()

def create_theme(name):
    conn = get_conn()
    with conn:
        conn.execute("INSERT OR IGNORE INTO themes(name) VALUES (?)", (name,))

def delete_theme(theme_id):
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM themes WHERE id = ?", (theme_id,))

def list_projects(theme_id=None):
    conn = get_conn()
    if theme_id:
        return conn.execute("SELECT id, theme_id, name FROM projects WHERE theme_id=? ORDER BY name", (theme_id,)).fetchall()
    return conn.execute("SELECT id, theme_id, name FROM projects ORDER BY name").fetchall()

def create_project(theme_id, name):
    conn = get_conn()
    with conn:
        conn.execute("INSERT OR IGNORE INTO projects(theme_id, name) VALUES (?,?)", (theme_id, name))

def delete_project(project_id):
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

def create_meeting(theme_id, project_id, title, date, participants, source, transcript_path, summary):
    conn = get_conn()
    with conn:
        cur = conn.execute("""
            INSERT INTO meetings(theme_id, project_id, title, date, participants, source, transcript_path, summary, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (theme_id, project_id, title, date, participants, source, transcript_path, summary or "", now_ts()))
        return cur.lastrowid

def update_meeting(meeting_id, **fields):
    if not fields: return
    keys = ", ".join([f"{k}=?" for k in fields.keys()])
    params = list(fields.values()) + [meeting_id]
    conn = get_conn()
    with conn:
        conn.execute(f"UPDATE meetings SET {keys} WHERE id=?", params)
