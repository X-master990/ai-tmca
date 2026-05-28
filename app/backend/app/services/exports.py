"""把 records 匯出成 Excel(.xlsx) — 總表 / 續約名單 / 搜尋結果共用。

完整欄位、依總表順序輸出。用 getattr 取值(缺欄位自動跳過 None),跨版本安全。
"""
from __future__ import annotations

import json
from datetime import date, datetime
from io import BytesIO
from typing import Iterable

from openpyxl import Workbook

# (欄位屬性, 中文表頭) — 對齊 IMPORT-MAPPING / 總表全欄位順序
EXPORT_COLUMNS: list[tuple[str, str]] = [
    ("category_code", "類別代碼"),
    ("cert_no", "證書編號"),
    ("issued_date", "發證日"),
    ("invoice_date", "發票日期"),
    ("invoice_type", "發票形式"),
    ("invoice_title", "發票抬頭"),
    ("tax_id", "統一編號"),
    ("invoice_no", "發票號碼"),
    ("amount", "金額(含稅)"),
    ("source", "提報"),
    ("officer", "承辦人"),
    ("action_type", "辦理項目"),
    ("apply_date", "申請日期"),
    ("applicant_name", "申請人"),
    ("applicant_id", "身分證號"),
    ("applicant_mobile", "行動"),
    ("applicant_phone", "電話"),
    ("applicant_fax", "傳真"),
    ("holder_name", "持證者"),
    ("holder_type", "性質/類型"),
    ("use_zip", "郵遞區號"),
    ("use_address", "使用地址"),
    ("onsite_name", "現場聯絡人"),
    ("onsite_mobile", "現場手機"),
    ("onsite_phone", "現場電話"),
    ("onsite_ext", "分機"),
    ("onsite_fax", "現場傳真"),
    ("qty", "數量/台數"),
    ("brand", "廠牌"),
    ("serial_no", "機號"),
    ("period_start", "授權起"),
    ("period_end", "授權迄"),
    ("mail_type", "郵件形式"),
    ("mail_zip", "寄證郵區"),
    ("mail_address", "寄證地址"),
    ("mail_recipient", "收件人"),
    ("mail_phone", "收件人電話"),
    ("issuance_status", "核發狀態"),
    ("renewal_status", "續約狀態"),
    ("note", "註記"),
    ("extra", "其他資料(JSON)"),
]


def _cell(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.replace(microsecond=0).isoformat(sep=" ")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False) if v else None
    return v


def build_records_xlsx(records: Iterable, sheet_title: str = "總表") -> bytes:
    """records: Record ORM 物件 iterable。回傳 .xlsx bytes。"""
    wb = Workbook()
    ws = wb.active
    ws.title = (sheet_title or "Sheet1")[:31]
    ws.append([h for _, h in EXPORT_COLUMNS])
    for r in records:
        ws.append([_cell(getattr(r, attr, None)) for attr, _ in EXPORT_COLUMNS])
    ws.freeze_panes = "A2"  # 凍結表頭列
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
