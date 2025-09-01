import pandas as pd
from .utils import EXPORTS_DIR
from .db import get_conn
from pathlib import Path
from datetime import datetime

def export_excel(theme_id=None, project_id=None):
    conn = get_conn()
    # CR
    cr_rows = conn.execute("""
        SELECT id, title, date, COALESCE(participants,''), COALESCE(source,''), COALESCE(summary,''), COALESCE(transcript_path,'')
        FROM meetings
        WHERE (? IS NULL OR theme_id=?)
          AND (? IS NULL OR project_id=?)
        ORDER BY date DESC, id DESC
    """, (theme_id, theme_id, project_id, project_id)).fetchall()
    cr_df = pd.DataFrame([{
        "MeetingID": r[0], "Titre": r[1], "Date": r[2], "Participants": r[3],
        "Source": r[4], "Résumé": r[5], "TranscriptPath": r[6]
    } for r in cr_rows])

    # ToDo courant
    todo_rows = conn.execute("""
        SELECT id, meeting_id, action, COALESCE(actor,''), COALESCE(due_date,''), status, created_at
        FROM todos
        WHERE (? IS NULL OR theme_id=?)
          AND (? IS NULL OR project_id=?)
        ORDER BY CASE status WHEN 'Ouvert' THEN 0 ELSE 1 END, COALESCE(due_date,''), id DESC
    """, (theme_id, theme_id, project_id, project_id)).fetchall()
    todo_df = pd.DataFrame([{
        "ToDoID": r[0], "MeetingID": r[1] or "", "Action": r[2], "Acteur": r[3],
        "Échéance": r[4], "Statut": r[5], "Créé": r[6]
    } for r in todo_rows])

    # ToDo Global
    todo_glob = conn.execute("""
        SELECT t.id, th.name, p.name, m.id, m.date, m.title,
               t.action, COALESCE(t.actor,''), COALESCE(t.due_date,''), t.status, t.created_at
        FROM todos t
        LEFT JOIN themes th ON th.id = t.theme_id
        LEFT JOIN projects p ON p.id = t.project_id
        LEFT JOIN meetings m ON m.id = t.meeting_id
        ORDER BY COALESCE(m.date, ''), t.id
    """).fetchall()
    todo_global_df = pd.DataFrame([{
        "ToDoID": r[0], "Thématique (Domaine)": r[1] or "", "Projet (Sujet)": r[2] or "",
        "MeetingID": r[3] or "", "Date réunion": r[4] or "", "Titre réunion": r[5] or "",
        "Action": r[6] or "", "Acteur": r[7] or "", "Échéance": r[8] or "",
        "Statut": r[9] or "", "Créé": r[10] or ""
    } for r in todo_glob])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(EXPORTS_DIR) / f"export_CR_ToDo_{ts}.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        cr_df.to_excel(writer, index=False, sheet_name="CR")
        todo_df.to_excel(writer, index=False, sheet_name="ToDo")
        todo_global_df.to_excel(writer, index=False, sheet_name="ToDo_Global")
    return str(path)
