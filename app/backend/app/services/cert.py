"""證書生成 — 讀正面證書模板(Word 合併列印 MERGEFIELD) → 依欄位名填值 → 回 .docx bytes。

模板：/var/tmca/templates/證書/<各類別正面>.docx（已隨映像打包、已 git 追蹤）。
用 docx-mailmerge2 依「合併欄位名」(«持證者»、«證號»、«起年»…) 填值，
模板版面 / 字型 / Logo 完全不動，也不修改模板檔。

對應原則（依使用者指定）：
- 告別式(FUNERAL) 不出證書（無對應）。
- 社區管委會 / 公益伴唱機 借用電腦伴唱機證書。
- 其餘類別各自對應正面模板。

合併欄位名跨模板不一致（證號/證書編號、持證人/持證者、使用地址/營業地址），
用一張統一 resolver 對應回 Record；模板沒有的欄位回空字串（由前端表單補填）。

注意：各正面模板的「發證日期」是模板內固定文字（非合併欄位），本服務不改動它。
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from mailmerge import MailMerge

from app.config import settings
from app.models import Record

TEMPLATE_DIR = Path(settings.template_dir) / "證書"

# 類別代碼 → 正面證書模板檔名（檔案已存在於 templates/證書/，已部署）
CATEGORY_TO_TEMPLATE: dict[str, str] = {
    "COMPUTER_KARAOKE": "A2電腦伴唱機證書-正面.docx",
    "PUBLIC_KARAOKE":   "A2電腦伴唱機證書-正面.docx",   # 借用電腦伴唱機證書
    "COMMUNITY_BOARD":  "A2電腦伴唱機證書-正面.docx",   # 借用電腦伴唱機證書
    "SELF_SERVICE_KTV": "B1自助式KTV證書-正面.docx",
    "STREET_ARTIST":    "E1街頭藝人授權證書-正面.docx",
    "TRANSPORT":        "H1交通運輸工具證書-正面.docx",
    "SINGLE_EVENT":     "D2單場次表演證書-正面.docx",
    "PUBLIC_TRANSMIT":  "公開傳輸證書-正面.docx",
    "AREA_DISPLAY":     "音樂著作公開播送授權證書-坪數及顯示器.docx",
    "HALL_ROOM":        "音樂著作公開播送授權證書 -大廳、客房、宴會廳-正面.docx",
    "ELECTION":         "F4競選活動證書-正面.docx",
    # FUNERAL（告別式）：不出證書
}


def has_cert(category_code: str) -> bool:
    return category_code in CATEGORY_TO_TEMPLATE


def template_path_for(category_code: str) -> Path | None:
    fn = CATEGORY_TO_TEMPLATE.get(category_code)
    return (TEMPLATE_DIR / fn) if fn else None


# ── 民國日期分件（起年/起月/起日…）────────────────────────────
def _roc_year(d: date | None) -> str:
    return str(d.year - 1911) if d else ""


def _month(d: date | None) -> str:
    return str(d.month) if d else ""


def _day(d: date | None) -> str:
    return str(d.day) if d else ""


def _extra(rec: Record, key: str):
    return (rec.extra or {}).get(key)


def _xml_safe(s: str) -> str:
    """移除 XML 不接受的控制字元（保留 \\t \\n \\r）。

    lxml 寫值遇到 NULL/控制字元會丟 ValueError；先清掉，產證書不會因此失敗。
    """
    return "".join(c for c in s if c in "\t\n\r" or ord(c) >= 0x20)


def _resolve_field(name: str, rec: Record) -> str:
    """單一合併欄位名 → Record 對應值（字串；無對應或 None 回空字串）。"""
    ps, pe = rec.period_start, rec.period_end
    table = {
        # 共通（不同模板用不同名稱，皆對同一欄）
        "證號": rec.cert_no, "證書編號": rec.cert_no,
        "持證人": rec.holder_name, "持證者": rec.holder_name,
        "使用地址": rec.use_address, "營業地址": rec.use_address,
        "起年": _roc_year(ps), "起月": _month(ps), "起日": _day(ps),
        "終年": _roc_year(pe), "終月": _month(pe), "終日": _day(pe),
        # 標的數量 / 廠牌 / 機號 / 車牌
        "台數": rec.qty, "客房書": rec.qty,
        "廠牌名稱": rec.brand, "機號": rec.serial_no,
        "車牌號碼": rec.serial_no,
        # 類別專屬（多放在 extra）
        "坪數": _extra(rec, "floor_area"),
        "藝人證號": _extra(rec, "street_cert_no"),
        "平台名稱": _extra(rec, "platform_name"),
        "網址": _extra(rec, "platform_url"),
        "曲目": _extra(rec, "songs"), "演出曲目": _extra(rec, "songs"),
        "總曲數": _extra(rec, "song_count"), "首": _extra(rec, "song_count"),
        "節目名稱": _extra(rec, "event_name"),
        "活動地點": _extra(rec, "venue"),
        "地點地址": _extra(rec, "venue_address"),
        # 其餘模板特有欄位（每場活動場 / 特定曲目場…）→ 無對應，留白給前端補
    }
    v = table.get(name)
    return "" if v is None else str(v)


def merge_fields_for(category_code: str) -> list[str]:
    """回該類別模板的合併欄位名（排序）；無模板或檔案不存在回空 list。"""
    p = template_path_for(category_code)
    if not p or not p.exists():
        return []
    with MailMerge(str(p)) as doc:
        return sorted(doc.get_merge_fields())


def build_cert_prefill(rec: Record) -> dict:
    """回 {template, fields:[{name,value}]} — 依模板實際合併欄位逐欄預填。"""
    fn = CATEGORY_TO_TEMPLATE.get(rec.category_code)
    if not fn:
        return {"template": None, "fields": []}
    p = TEMPLATE_DIR / fn
    if not p.exists():
        raise FileNotFoundError(f"證書模板不存在：{p}")
    with MailMerge(str(p)) as doc:
        names = sorted(doc.get_merge_fields())
    return {
        "template": fn,
        "fields": [{"name": n, "value": _resolve_field(n, rec)} for n in names],
    }


def render_cert(category_code: str, values: dict[str, str]) -> bytes:
    """以 values 填該類別正面模板的合併欄位，回 .docx bytes。

    缺的欄位一律補空字串 → 清掉模板上的 «欄位» 佔位符。
    """
    fn = CATEGORY_TO_TEMPLATE.get(category_code)
    if not fn:
        raise ValueError(f"類別 {category_code} 無對應證書模板")
    p = TEMPLATE_DIR / fn
    if not p.exists():
        raise FileNotFoundError(f"證書模板不存在：{p}")

    with MailMerge(str(p)) as doc:
        names = doc.get_merge_fields()
        merged = {n: _xml_safe(str(values.get(n, "") or "")) for n in names}
        doc.merge(**merged)
        buf = BytesIO()
        doc.write(buf)
        return buf.getvalue()
