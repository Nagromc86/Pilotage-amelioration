import sqlite3
from .utils import DB_PATH
def get_conn(): DB_PATH.parent.mkdir(parents=True, exist_ok=True); return sqlite3.connect(DB_PATH)
def init_db():
    con=get_conn(); cur=con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS meetings (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL);")
    cur.execute("CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT);")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);")
    con.commit()
    # Ensure required columns exist
    def ensure_cols(table, cols):
        cur.execute(f'PRAGMA table_info({table})'); existing=[r[1] for r in cur.fetchall()]
        for col,typ in cols:
            if col not in existing: cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {typ}')
    ensure_cols('meetings', [('thematique','TEXT'),('projet','TEXT'),('participants','TEXT'),('title','TEXT'),('content','TEXT'),('audio_path','TEXT')])
    ensure_cols('todos', [('meeting_id','INTEGER'),('thematique','TEXT'),('projet','TEXT'),('action','TEXT'),('acteur','TEXT'),('echeance','TEXT'),('status','TEXT')])
    con.commit(); con.close()
def add_meeting(date, thematique, projet, title, participants, content, audio_path):
    con=get_conn(); cur=con.cursor()
    cur.execute('INSERT INTO meetings(date,thematique,projet,title,participants,content,audio_path) VALUES (?,?,?,?,?,?,?)',(date,thematique,projet,title,participants,content,audio_path)); con.commit(); mid=cur.lastrowid; con.close(); return mid
def update_meeting(mid, **kwargs):
    if not kwargs: return
    con=get_conn(); cur=con.cursor(); q=','.join([f'{k}=?' for k in kwargs]); cur.execute(f'UPDATE meetings SET {q} WHERE id=?', (*kwargs.values(),mid)); con.commit(); con.close()
def get_meeting(mid):
    con=get_conn(); cur=con.cursor(); cur.execute('SELECT id,date,thematique,projet,title,participants,content FROM meetings WHERE id=?',(mid,)); row=cur.fetchone(); con.close(); return row
def list_meetings(filters=None):
    con=get_conn(); cur=con.cursor(); q='SELECT id,date,thematique,projet,title,participants,content FROM meetings'; params=[]
    if filters: 
        clauses=[f'{k} LIKE ?' for k in filters]; params=[f'%{v}%' for v in filters.values()]; 
        if clauses: q += ' WHERE ' + ' AND '.join(clauses)
    q += ' ORDER BY date DESC, id DESC'; cur.execute(q, params); rows=cur.fetchall(); con.close(); return rows
def add_todo(meeting_id, thematique, projet, action, acteur, echeance, status='A faire'):
    con=get_conn(); cur=con.cursor(); cur.execute('INSERT INTO todos(meeting_id,thematique,projet,action,acteur,echeance,status) VALUES (?,?,?,?,?,?,?)',(meeting_id,thematique,projet,action,acteur,echeance,status)); con.commit(); con.close()
def list_todos():
    con=get_conn(); cur=con.cursor(); cur.execute('SELECT id,meeting_id,thematique,projet,action,acteur,echeance,status FROM todos ORDER BY id DESC'); rows=cur.fetchall(); con.close(); return rows
