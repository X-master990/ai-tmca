"""Records API"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import allowed_fields
from app.database import get_db
from app.models import AuditLog, Category, Record, User
from app.schemas.record import RecordOut

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("", response_model=list[RecordOut])
def list_records(
    category_code: str = Query(..., description="category code，例：COMPUTER_KARAOKE"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """回該 category 的全部 records（無分頁，Phase 3a 策略）。"""
    if not db.query(Category).filter(Category.code == category_code).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Category {category_code} 不存在")
    rows = (
        db.query(Record)
        .filter(Record.category_code == category_code)
        .order_by(Record.issued_date.desc().nulls_first(), Record.id.desc())
        .all()
    )
    return rows


class PermissionsOut(BaseModel):
    role: str
    editable_fields_by_category: dict[str, list[str]]


@router.get("/permissions", response_model=PermissionsOut)
def get_permissions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """回該 user 在每個 category 可編輯的欄位清單，供前端 readonly 判定。"""
    cats = db.query(Category).all()
    return PermissionsOut(
        role=user.role,
        editable_fields_by_category={
            c.code: sorted(allowed_fields(user.role, c.code)) for c in cats
        },
    )


class RecordPatch(BaseModel):
    """單欄/多欄更新。值型態由後端按欄位轉。"""

    # 用 dict 接收動態欄位
    model_config = {"extra": "allow"}


DATE_FIELDS = {
    "issued_date", "invoice_date", "apply_date", "period_start", "period_end",
}
INT_FIELDS = {"amount", "qty"}
BOOL_FIELDS = {"paper_application", "paper_remittance", "paper_official_doc"}


def _coerce(field: str, raw):
    """把前端傳來的字串/null 轉成正確型態。"""
    if raw is None or raw == "":
        return None
    if field in DATE_FIELDS:
        if isinstance(raw, str):
            # 接受 ISO yyyy-mm-dd
            try:
                return date.fromisoformat(raw)
            except ValueError:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{field} 日期格式錯誤，請用 YYYY-MM-DD")
        if isinstance(raw, date):
            return raw
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{field} 必須是日期")
    if field in INT_FIELDS:
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{field} 必須是整數")
    if field in BOOL_FIELDS:
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("true", "1", "yes", "y", "t")
    return str(raw)


@router.post("", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
def create_record(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """新增 record。承辦/admin 才能用；類型必須是該角色負責的。"""
    category_code = body.pop("category_code", None)
    if not category_code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "缺 category_code")
    if not db.query(Category).filter(Category.code == category_code).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Category {category_code} 不存在")

    permitted = allowed_fields(user.role, category_code)
    if not permitted:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"無權新增 {category_code} 類型")

    rejected = [f for f in body.keys() if f not in permitted]
    if rejected:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"以下欄位無寫入權: {', '.join(rejected)}",
        )

    payload: dict = {}
    for field, raw in body.items():
        # 忽略空字串、None、空白：當作未填，讓 DB default / NULL
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            continue
        payload[field] = _coerce(field, raw)

    rec = Record(
        category_code=category_code,
        issuance_status="紅",
        created_by=user.id,
        updated_by=user.id,
        **payload,
    )
    # 如果有填發票號 → 直接綠燈
    if payload.get("invoice_no"):
        rec.issuance_status = "綠"

    db.add(rec)
    db.commit()
    db.refresh(rec)

    db.add(AuditLog(
        record_id=rec.id,
        user_id=user.id,
        field_name="__created__",
        old_value=None,
        new_value=category_code,
    ))
    db.commit()
    return rec


@router.patch("/{record_id}", response_model=RecordOut)
def patch_record(
    record_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到 record")

    permitted = allowed_fields(user.role, rec.category_code)
    if not permitted:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "無編輯權限")

    rejected = [f for f in body.keys() if f not in permitted]
    if rejected:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"以下欄位無編輯權: {', '.join(rejected)}",
        )

    changes = []
    for field, raw in body.items():
        new_val = _coerce(field, raw)
        old_val = getattr(rec, field)
        if old_val == new_val:
            continue
        setattr(rec, field, new_val)
        changes.append((field, old_val, new_val))

    if not changes:
        return rec

    # 連帶副作用：填了發票號碼 → issuance_status 自動轉綠
    if any(f == "invoice_no" for f, _, _ in changes):
        if rec.invoice_no and rec.issuance_status != "綠":
            old = rec.issuance_status
            rec.issuance_status = "綠"
            changes.append(("issuance_status", old, "綠"))

    rec.updated_by = user.id
    rec.updated_at = datetime.utcnow()

    for field, old_val, new_val in changes:
        db.add(AuditLog(
            record_id=rec.id,
            user_id=user.id,
            field_name=field,
            old_value=None if old_val is None else str(old_val),
            new_value=None if new_val is None else str(new_val),
        ))

    db.commit()
    db.refresh(rec)
    return rec
