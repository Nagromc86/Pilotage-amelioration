from pathlib import Path
import pandas as pd
def export_excel(path: Path, meetings_rows, todos_rows):
    cr_cols = ['ID','Date','Thématique','Projet','Titre','Participants','CR']
    cr_df = pd.DataFrame(meetings_rows, columns=cr_cols)
    todo_cols = ['ID','MeetingID','Thématique','Projet','Action','Acteur','Échéance','Statut']
    todo_df = pd.DataFrame(todos_rows, columns=todo_cols)
    m_df = cr_df[['ID','Date','Thématique','Projet']].rename(columns={'ID':'MeetingID'})
    glob_df = todo_df.merge(m_df, on='MeetingID', how='left')
    cols = ['Date','Thématique','Projet','Action','Acteur','Échéance','Statut','MeetingID']
    glob_df = glob_df[cols]
    with pd.ExcelWriter(path, engine='openpyxl') as xw:
        cr_df.to_excel(xw, sheet_name='CR', index=False)
        todo_df.to_excel(xw, sheet_name='ToDo', index=False)
        glob_df.to_excel(xw, sheet_name='ToDo_Global', index=False)