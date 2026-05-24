"""客戶編號（customer_no）規則與指派。

規則（使用者 2026-05-24 確認）：7 碼 = 1 碼類別前綴 + 6 碼流水。
- 一店家一號：同前綴下「持證者名稱 + 統一編號」完全相同 → 視為同一店家共用一號。
- 流水各前綴各自從 000001 起。
- 第一碼類別前綴對應如下（8 公播目前無對應類型）。
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Record

PREFIX_BY_CATEGORY: dict[str, str] = {
    "COMPUTER_KARAOKE": "1",  # 電腦伴唱機（營利性）
    "COMMUNITY_BOARD": "1",   # 社區管委會（管委會）
    "SELF_SERVICE_KTV": "2",  # 自助KTV
    "PUBLIC_KARAOKE": "3",    # 公益伴唱機（文化教育/公益）
    "STREET_ARTIST": "4",     # 街頭藝人
    "HALL_ROOM": "5",         # 大廳-宴會廳-客房（旅館飯店）
    "AREA_DISPLAY": "5",      # 坪數-顯示器（營業商號）
    "TRANSPORT": "6",         # 交通運輸工具
    "SINGLE_EVENT": "7",      # 單場次表演
    "FUNERAL": "7",           # 告別式
    "ELECTION": "7",          # 競選活動
    "PUBLIC_TRANSMIT": "9",   # 公開傳輸（公傳）
}


def prefix_for(category_code: str) -> str | None:
    return PREFIX_BY_CATEGORY.get(category_code)


def _norm(s: str | None) -> str:
    return (s or "").strip()


def find_existing_no(db: Session, prefix: str, holder_name: str, tax_id: str | None) -> str | None:
    """同前綴、同(持證者名稱+統編) 已配發過的客戶編號 → 沿用。"""
    row = (
        db.query(Record.customer_no)
        .filter(Record.customer_no.isnot(None))
        .filter(Record.customer_no.like(f"{prefix}%"))
        .filter(func.trim(Record.holder_name) == holder_name)
        .filter(func.coalesce(func.trim(Record.tax_id), "") == (tax_id or ""))
        .first()
    )
    return row[0] if row else None


def next_serial(db: Session, prefix: str) -> int:
    """該前綴目前最大流水 + 1。"""
    mx = (
        db.query(func.max(Record.customer_no))
        .filter(Record.customer_no.like(f"{prefix}%"))
        .scalar()
    )
    return (int(mx[1:]) + 1) if mx else 1


def assign_for_record(db: Session, rec: Record) -> str | None:
    """為單筆 record 指派客戶編號（新增 / 續約時用）。
    已有號、無對應前綴、或無持證者 → 不動。回傳指派的號（或 None）。"""
    if rec.customer_no:
        return rec.customer_no
    prefix = prefix_for(rec.category_code)
    holder = _norm(rec.holder_name)
    if not prefix or not holder:
        return None
    tax = _norm(rec.tax_id)
    existing = find_existing_no(db, prefix, holder, tax)
    if existing:
        rec.customer_no = existing
        return existing
    serial = next_serial(db, prefix)
    rec.customer_no = f"{prefix}{serial:06d}"
    return rec.customer_no
