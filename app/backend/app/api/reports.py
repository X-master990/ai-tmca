"""Reports API — Dashboard 統計數據"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.database import get_db
from app.models import Category, Record, User

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
def summary(
    year: int | None = Query(None, description="預設今年。<1911 視為民國年"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("accountant", "admin")),
):
    """報表 dashboard。僅會計 / admin 可看。"""
    if year is None:
        year = datetime.utcnow().year
    elif year < 1911:
        year = year + 1911

    # 每月新核發數 + 收入
    by_month_rows = (
        db.query(
            func.extract("month", Record.issued_date).label("m"),
            func.count(Record.id).label("n"),
            func.coalesce(func.sum(Record.amount), 0).label("total_amount"),
        )
        .filter(func.extract("year", Record.issued_date) == year)
        .group_by("m")
        .order_by("m")
        .all()
    )

    months = []
    for m in range(1, 13):
        row = next((r for r in by_month_rows if int(r.m) == m), None)
        months.append({
            "month": m,
            "issued_count": int(row.n) if row else 0,
            "amount_sum": int(row.total_amount) if row else 0,
        })

    # 各 category 累計（year 內）
    by_cat_rows = (
        db.query(
            Record.category_code,
            func.count(Record.id).label("n"),
            func.coalesce(func.sum(Record.amount), 0).label("amt"),
        )
        .filter(func.extract("year", Record.issued_date) == year)
        .group_by(Record.category_code)
        .all()
    )
    cat_name_map = {c.code: c.name_zh for c in db.query(Category).all()}
    by_category = [
        {
            "code": r.category_code,
            "name_zh": cat_name_map.get(r.category_code, r.category_code),
            "issued_count": int(r.n),
            "amount_sum": int(r.amt),
        }
        for r in sorted(by_cat_rows, key=lambda x: -int(x.n))
    ]

    # 續約率（年內到期的）：綠 / (紅+綠)
    renewal_breakdown = dict(
        db.query(Record.renewal_status, func.count(Record.id))
        .filter(func.extract("year", Record.period_end) == year)
        .group_by(Record.renewal_status)
        .all()
    )
    renewed = renewal_breakdown.get("綠", 0)
    unrenewed = renewal_breakdown.get("紅", 0)
    other = renewal_breakdown.get("灰", 0) + (renewal_breakdown.get(None, 0))
    denom = renewed + unrenewed
    renewal_rate = round(renewed / denom * 100, 1) if denom else None

    # 總體
    total_issued_year = sum(m["issued_count"] for m in months)
    total_amount_year = sum(m["amount_sum"] for m in months)
    total_records = db.query(func.count(Record.id)).scalar()

    # 核發狀態（含歷史全部）
    issuance_breakdown = dict(
        db.query(Record.issuance_status, func.count(Record.id))
        .group_by(Record.issuance_status)
        .all()
    )

    return {
        "year": year,
        "totals": {
            "issued_this_year": total_issued_year,
            "amount_this_year": total_amount_year,
            "total_records": int(total_records or 0),
        },
        "monthly": months,
        "by_category": by_category,
        "renewal": {
            "renewed": renewed,
            "unrenewed": unrenewed,
            "other": other,
            "rate_percent": renewal_rate,
        },
        "issuance": {
            "issued": issuance_breakdown.get("綠", 0),
            "pending": issuance_breakdown.get("紅", 0),
        },
    }
