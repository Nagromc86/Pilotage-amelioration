from pathlib import Path
from typing import List, Dict
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

def export_excel(db_rows_cr: List[Dict], db_rows_todo: List[Dict], out_path: Path):
    wb=Workbook(); ws_cr=wb.active; ws_cr.title='CR'
    headers_cr=['ID','Date','Thématique','Projet','Participants','Contenu']; ws_cr.append(headers_cr)
    for r in db_rows_cr:
        ws_cr.append([r['id'], r['date'], r.get('thematique',''), r.get('projet',''), r.get('participants',''), r.get('content','')])
    ws_t=wb.create_sheet('ToDo')
    headers_t=['ID','Meeting_ID','Thématique','Projet','Action','Acteur','Échéance']; ws_t.append(headers_t)
    for r in db_rows_todo:
        ws_t.append([r['id'], r.get('meeting_id',''), r.get('thematique',''), r.get('projet',''), r.get('action',''), r.get('acteur',''), r.get('echeance','')])
    ws_g=wb.create_sheet('ToDo_Global')
    headers_g=['Meeting_Date','Thématique','Projet','Action','Acteur','Échéance']; ws_g.append(headers_g)
    meet_map={r['id']: r['date'] for r in db_rows_cr}
    for r in db_rows_todo:
        ws_g.append([meet_map.get(r.get('meeting_id'),''), r.get('thematique',''), r.get('projet',''), r.get('action',''), r.get('acteur',''), r.get('echeance','')])
    for ws in (ws_cr, ws_t, ws_g):
        for col in range(1, ws.max_column+1): ws.column_dimensions[get_column_letter(col)].width=24
        for cell in ws[1]:
            cell.font=Font(bold=True); cell.fill=PatternFill('solid', fgColor='E6F0FF'); cell.alignment=Alignment(horizontal='center')
    wb.save(str(out_path))
