"""匯出 API — 總表 / 續約名單 / 搜尋結果 → Excel(.xlsx)

全部資料、完整欄位,後端產生,不受前端 500 列上限影響(對應需求 D5)。
"""
from datetime import datetime
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import extract, or_, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Category, Record, User
from app.services.exports import build_records_xlsx

router = APIRouter(prefix="/api/exports", tags=["exports"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _stream(xlsx_bytes: bytes, fname: str) -> StreamingResponse:
    # 檔名含中文 → RFC5987 filename*；保留 ASCII fallback
    cd = f"attachment; filename=export.xlsx; filename*=UTF-8''{quote(fname)}"
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": cd},
    )


@router.get("/records")
def export_records(
    category_code: str = Query(..., description="category code"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """匯出某類別的全部總表資料(排除軟刪除)。"""
    cat = db.query(Category).filter(Category.code == category_code).first()
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Category {category_code} 不存在")
    rows = (
        db.query(Record)
        .filter(Record.category_code == category_code, Record.deleted_at.is_(None))
        .order_by(Record.issued_date.desc().nulls_last(), Record.id.desc())
        .all()
    )
    name = getattr(cat, "name_zh", None) or category_code
    xlsx = build_records_xlsx(rows, sheet_title=name)
    return _stream(xlsx, f"總表_{name}_{datetime.now():%Y%m%d}.xlsx")


@router.get("/renewals")
def export_renewals(
    month: int = Query(..., ge=1, le=12),
    year: int | None = Query(None),
    category_code: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """匯出某年月到期的續約名單(含續約狀態欄,未續約=紅/灰、已續約=綠)。"""
    if year is None:
        year = datetime.utcnow().year
    elif year < 1911:
        year = year + 1911
    q = (
        db.query(Record)
        .filter(extract("year", Record.period_end) == year)
        .filter(extract("month", Record.period_end) == month)
        .filter(Record.deleted_at.is_(None))
    )
    if category_code:
        q = q.filter(Record.category_code == category_code)
    # 已續約(綠)排後、未續約排前;同組依到期日
    rows = q.order_by(Record.renewal_status.desc(), Record.period_end, Record.id).all()
    xlsx = build_records_xlsx(rows, sheet_title=f"{year}-{month:02d}續約")
    return _stream(xlsx, f"續約名單_{year}-{month:02d}.xlsx")


@router.get("/search")
def export_search(
    q: str = Query(..., min_length=1, max_length=120),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """匯出全文搜尋結果(與 /api/search 同樣的 FTS + LIKE 邏輯)。"""
    keyword = q.strip()
    like = f"%{keyword}%"
    ids_fts = [
        r.id
        for r in db.execute(
            text("SELECT id FROM records WHERE search_vec @@ plainto_tsquery('simple', :q)"),
            {"q": keyword},
        ).fetchall()
    ]
    fallback = (
        db.query(Record.id)
        .filter(
            or_(
                Record.holder_name.ilike(like),
                Record.applicant_name.ilike(like),
                Record.cert_no.ilike(like),
                Record.invoice_no.ilike(like),
                Record.tax_id.ilike(like),
                Record.invoice_title.ilike(like),
                Record.officer.ilike(like),
                Record.use_address.ilike(like),
            )
        )
        .limit(5000)
        .all()
    )
    ids = list(dict.fromkeys(ids_fts + [r.id for r in fallback]))
    rows = []
    if ids:
        rows = (
            db.query(Record)
            .filter(Record.id.in_(ids), Record.deleted_at.is_(None))
            .order_by(Record.issued_date.desc().nulls_last(), Record.id.desc())
            .all()
        )
    xlsx = build_records_xlsx(rows, sheet_title="搜尋結果")
    return _stream(xlsx, f"搜尋_{keyword}_{datetime.now():%Y%m%d}.xlsx")
