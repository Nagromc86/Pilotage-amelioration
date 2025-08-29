import pandas as pd
from .utils import EXPORTS_DIR
from .db import list_meetings, list_todos
from pathlib import Path
from datetime import datetime

def export_excel(theme_id=None, project_id=None):
    meetings = list_meetings(theme_id, project_id)
    todos = list_todos(theme_id, project_id, status=None)

    cr_rows = []
    for m in meetings:
        mid, theme_id, project_id, title, date, participants, source, transcript_path, summary, created_at = m
        cr_rows.append({"MeetingID": mid, "Titre": title, "Date": date, "Participants": participants or "", "Source": source or "", "Résumé": summary or "", "TranscriptPath": transcript_path or ""})
    cr_df = pd.DataFrame(cr_rows)

    todo_rows = []
    for t in todos:
        tid, th, pr, mid, action, actor, due, status, created_at = t
        todo_rows.append({"ToDoID": tid, "MeetingID": mid or "", "Action": action, "Acteur": actor or "", "Échéance": due or "", "Statut": status})
    todo_df = pd.DataFrame(todo_rows)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(EXPORTS_DIR) / f"export_CR_ToDo_{ts}.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        cr_df.to_excel(writer, index=False, sheet_name="CR")
        todo_df.to_excel(writer, index=False, sheet_name="ToDo")
    return str(path)
