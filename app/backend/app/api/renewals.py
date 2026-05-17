"""Renewals API — 續約偵測重算 + 月份清單"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, extract, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models import Record, User
from app.schemas.record import RecordOut
from app.services.renewals import compute_renewal_status

router = APIRouter(prefix="/api/renewals", tags=["renewals"])


@router.post("/recompute")
def recompute(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """手動觸發續約狀態重算（admin）。"""
    return compute_renewal_status(db)


@router.get("")
def list_renewals(
    month: int = Query(..., ge=1, le=12, description="1-12"),
    year: int | None = Query(None, description="預設為今年；指定年份用民國/西元都行（>1911 視為西元）"),
    category_code: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """依月份回該月到期 records，分為「未續約」與「已續約」兩組。"""
    if year is None:
        from datetime import datetime as _dt
        year = _dt.utcnow().year
    elif year < 1911:  # 看起來像民國年
        year = year + 1911

    q = (
        db.query(Record)
        .filter(extract("year", Record.period_end) == year)
        .filter(extract("month", Record.period_end) == month)
    )
    if category_code:
        q = q.filter(Record.category_code == category_code)

    rows = q.order_by(Record.period_end, Record.id).all()

    unrenewed = [RecordOut.model_validate(r) for r in rows if r.renewal_status == "紅"]
    renewed = [RecordOut.model_validate(r) for r in rows if r.renewal_status == "綠"]
    other = [RecordOut.model_validate(r) for r in rows if r.renewal_status not in ("紅", "綠")]

    return {
        "year": year,
        "month": month,
        "category_code": category_code,
        "summary": {
            "未續約": len(unrenewed),
            "已續約": len(renewed),
            "其他": len(other),
            "total": len(rows),
        },
        "unrenewed": unrenewed,
        "renewed": renewed,
        "other": other,
    }
