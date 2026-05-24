"""Renewals API — 續約偵測重算 + 月份清單 + 一鍵生成續約行"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.permissions import can_delete
from app.database import get_db
from app.models import AuditLog, Record, User
from app.schemas.record import RecordOut
from app.services.customer_no import assign_for_record
from app.services.renewals import compute_renewal_status

router = APIRouter(prefix="/api/renewals", tags=["renewals"])

# 生成續約行時，從舊紀錄複製過來的「可重用」欄位（個案專屬如金額/證號/發票/備註不帶）
_RENEWAL_CARRY_FIELDS = (
    "holder_name", "holder_type", "tax_id",
    "invoice_title", "invoice_type",
    "use_zip", "use_address",
    "mail_type", "mail_zip", "mail_address", "mail_recipient", "mail_phone",
    "applicant_name", "applicant_id", "applicant_mobile", "applicant_phone", "applicant_fax",
    "onsite_name", "onsite_mobile", "onsite_phone", "onsite_ext", "onsite_fax",
    "source", "officer",
)


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
    _: User = Depends(require_role("officer_a", "officer_b", "admin")),
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
        .filter(Record.deleted_at.is_(None))
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


def _plus_one_year_minus_day(start: date) -> date:
    """新授權迄日 = 起日 + 1 年 - 1 天（例 2027-01-01 → 2027-12-31）。"""
    try:
        one_year = start.replace(year=start.year + 1)
    except ValueError:  # 2/29 → 隔年無此日，退到 2/28
        one_year = start.replace(year=start.year + 1, day=28)
    return one_year - timedelta(days=1)


@router.post("/{record_id}/generate", response_model=RecordOut)
def generate_renewal(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("officer_a", "officer_b", "admin")),
):
    """一鍵生成續約行：複製舊紀錄的可重用欄位，辦理項目=續約，
    授權期間自舊到期日次日起算、預設一年（迄日可改），並重算續約狀態。"""
    old = db.query(Record).filter(Record.id == record_id).first()
    if not old or old.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到原紀錄")
    # 承辦限自己負責的類型（規則同刪除：admin 全部）
    if not can_delete(user.role, old.category_code):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "無權對此類型生成續約")
    if old.period_end is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "原紀錄無授權到期日，無法計算續約期間")

    start = old.period_end + timedelta(days=1)
    end = _plus_one_year_minus_day(start)

    new = Record(
        category_code=old.category_code,
        action_type="續約",
        apply_date=date.today(),
        period_start=start,
        period_end=end,
        extra=dict(old.extra or {}),
        issuance_status="紅",
        created_by=user.id,
        updated_by=user.id,
        **{f: getattr(old, f) for f in _RENEWAL_CARRY_FIELDS},
    )
    # 續約沿用同店家的客戶編號（找不到才配新號）
    new.customer_no = old.customer_no or assign_for_record(db, new)
    db.add(new)
    db.commit()
    db.refresh(new)

    db.add(AuditLog(
        record_id=new.id,
        user_id=user.id,
        field_name="__created__",
        old_value=f"renewal_of:{old.id}",
        new_value=old.category_code,
    ))
    db.commit()

    # 重算續約狀態：新行到期日較晚 → 舊行自動轉「綠」移出未續約名單
    compute_renewal_status(db)
    db.refresh(new)
    return new
