import pandas as pd
from .utils import EXPORTS_DIR
from .db import list_meetings, list_todos, get_conn
from pathlib import Path
from datetime import datetime

def _fetch_global_todos():
    conn = get_conn()
    sql = """
    SELECT
        t.id AS ToDoID,
        th.name AS Thematique,
        p.name AS Projet,
        m.id AS MeetingID,
        m.date AS DateReunion,
        m.title AS TitreReunion,
        t.action AS Action,
        COALESCE(t.actor, '') AS Acteur,
        COALESCE(t.due_date, '') AS Echeance,
        t.status AS Statut,
        t.created_at AS Cree
    FROM todos t
    LEFT JOIN themes th ON th.id = t.theme_id
    LEFT JOIN projects p ON p.id = t.project_id
    LEFT JOIN meetings m ON m.id = t.meeting_id
    ORDER BY COALESCE(m.date, ''), t.id
    """
    rows = conn.execute(sql).fetchall()
    out = []
    for r in rows:
        out.append({
            "ToDoID": r[0],
            "Thématique (Domaine)": r[1] or "",
            "Projet (Sujet)": r[2] or "",
            "MeetingID": r[3] or "",
            "Date réunion": r[4] or "",
            "Titre réunion": r[5] or "",
            "Action": r[6] or "",
            "Acteur": r[7] or "",
            "Échéance": r[8] or "",
            "Statut": r[9] or "",
            "Créé": r[10] or "",
        })
    return pd.DataFrame(out)

def export_excel(theme_id=None, project_id=None):
    meetings = list_meetings(theme_id, project_id)
    cr_rows = []
    for m in meetings:
        mid, theme_id, project_id, title, date, participants, source, transcript_path, summary, created_at = m
        cr_rows.append({"MeetingID": mid, "Titre": title, "Date": date, "Participants": participants or "", "Source": source or "", "Résumé": summary or "", "TranscriptPath": transcript_path or ""})
    cr_df = pd.DataFrame(cr_rows)

    todos = list_todos(theme_id, project_id, status=None)
    todo_rows = []
    for t in todos:
        tid, th, pr, mid, action, actor, due, status, created_at = t
        todo_rows.append({"ToDoID": tid, "MeetingID": mid or "", "Action": action, "Acteur": actor or "", "Échéance": due or "", "Statut": status, "Créé": created_at})
    todo_df = pd.DataFrame(todo_rows)

    todo_global_df = _fetch_global_todos()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(EXPORTS_DIR) / f"export_CR_ToDo_{ts}.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        cr_df.to_excel(writer, index=False, sheet_name="CR")
        todo_df.to_excel(writer, index=False, sheet_name="ToDo")
        todo_global_df.to_excel(writer, index=False, sheet_name="ToDo_Global")
    return str(path)
