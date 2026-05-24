"""Records API"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import allowed_fields, can_delete
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
        .filter(Record.deleted_at.is_(None))  # 軟刪除的不列出
        # 發證日優先、沒有則用申請日，新→舊；兩者皆無（新建/未發證）排最上面
        .order_by(
            func.coalesce(Record.issued_date, Record.apply_date).desc().nulls_first(),
            Record.id.desc(),
        )
        .all()
    )
    return rows


class HolderLookupOut(BaseModel):
    """承辦新增案件時的「持證者自動帶入」候選 — 過往同 holder/tax_id 紀錄的最近一筆，
    回傳「下次申請可重用」的聯絡 / 地址 / 抬頭欄位，個案專屬欄位（金額、日期、辦理項目、備註）不帶。"""
    id: int                   # 來源 record id（除錯用）
    category_code: str        # 上次屬於哪個類型
    last_apply_date: str | None  # 給前端顯示「上次申辦 = ...」做提示
    period_end: str | None    # 上次授權到期日 → 前端據此算新期間起算日（次日）
    holder_name: str | None
    holder_type: str | None
    tax_id: str | None
    invoice_title: str | None
    invoice_type: str | None
    use_zip: str | None
    use_address: str | None
    mail_zip: str | None
    mail_address: str | None
    mail_recipient: str | None
    mail_phone: str | None
    applicant_name: str | None
    applicant_id: str | None
    applicant_mobile: str | None
    applicant_phone: str | None
    applicant_fax: str | None
    onsite_name: str | None
    onsite_mobile: str | None
    onsite_phone: str | None
    onsite_ext: str | None
    onsite_fax: str | None


@router.get("/lookup", response_model=list[HolderLookupOut])
def lookup_holder(
    q: str = Query(..., min_length=1, description="持證者名稱或統一編號片段"),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """承辦在「新增案件」時，打持證者名稱即時搜尋過往紀錄，回傳可重用欄位的候選清單。
    去重邏輯：同 (holder_name, tax_id) 只保留最新（id 最大）的那筆。"""
    s = q.strip()
    if not s:
        return []
    like = f"%{s}%"
    rows = (
        db.query(Record)
        .filter(or_(
            Record.holder_name.ilike(like),
            Record.invoice_title.ilike(like),
            Record.tax_id.ilike(like),
        ))
        .filter(Record.deleted_at.is_(None))
        .order_by(Record.id.desc())
        .limit(200)  # 多撈一點再去重
        .all()
    )
    seen: set[tuple[str, str]] = set()
    out: list[HolderLookupOut] = []
    for r in rows:
        key = ((r.holder_name or "").strip(), (r.tax_id or "").strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(HolderLookupOut(
            id=r.id,
            category_code=r.category_code,
            last_apply_date=r.apply_date.isoformat() if r.apply_date else None,
            period_end=r.period_end.isoformat() if r.period_end else None,
            holder_name=r.holder_name,
            holder_type=r.holder_type,
            tax_id=r.tax_id,
            invoice_title=r.invoice_title,
            invoice_type=r.invoice_type,
            use_zip=r.use_zip,
            use_address=r.use_address,
            mail_zip=r.mail_zip,
            mail_address=r.mail_address,
            mail_recipient=r.mail_recipient,
            mail_phone=r.mail_phone,
            applicant_name=r.applicant_name,
            applicant_id=r.applicant_id,
            applicant_mobile=r.applicant_mobile,
            applicant_phone=r.applicant_phone,
            applicant_fax=r.applicant_fax,
            onsite_name=r.onsite_name,
            onsite_mobile=r.onsite_mobile,
            onsite_phone=r.onsite_phone,
            onsite_ext=r.onsite_ext,
            onsite_fax=r.onsite_fax,
        ))
        if len(out) >= limit:
            break
    return out


class PermissionsOut(BaseModel):
    role: str
    editable_fields_by_category: dict[str, list[str]]
    deletable_categories: list[str]


@router.get("/permissions", response_model=PermissionsOut)
def get_permissions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """回該 user 在每個 category 可編輯的欄位清單 + 可刪除的類型，供前端 UI 判定。"""
    cats = db.query(Category).all()
    return PermissionsOut(
        role=user.role,
        editable_fields_by_category={
            c.code: sorted(allowed_fields(user.role, c.code)) for c in cats
        },
        deletable_categories=[c.code for c in cats if can_delete(user.role, c.code)],
    )


class RecordPatch(BaseModel):
    """單欄/多欄更新。值型態由後端按欄位轉。"""

    # 用 dict 接收動態欄位
    model_config = {"extra": "allow"}


DATE_FIELDS = {
    "issued_date", "invoice_date", "apply_date", "period_start", "period_end",
}
INT_FIELDS = {"amount", "qty", "extra.audience_size", "extra.floor_area"}
BOOL_FIELDS = {"paper_application", "paper_remittance", "paper_official_doc"}


def _get_field(rec: Record, field: str):
    """讀欄位值，支援 "extra.<key>" 取 JSONB 子欄位。"""
    if field.startswith("extra."):
        return (rec.extra or {}).get(field[len("extra."):])
    return getattr(rec, field)


def _set_field(rec: Record, field: str, value) -> None:
    """寫欄位值，支援 "extra.<key>"。JSONB 需整個重新賦值，
    in-place mutation 不會被 SQLAlchemy 追蹤到。"""
    if field.startswith("extra."):
        key = field[len("extra."):]
        new_extra = dict(rec.extra or {})
        if value is None:
            new_extra.pop(key, None)
        else:
            new_extra[key] = value
        rec.extra = new_extra
    else:
        setattr(rec, field, value)


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


UNDO_WINDOW_MINUTES = 30
SYSTEM_AUDIT_FIELDS = ("__created__", "__invoice_issued__", "__deleted__", "__restored__")
# issuance_status 是 PATCH invoice_no 的副作用，不算「使用者直接編輯」；
# 找 undo 目標時跳過它，避免找到副作用而非主要動作
SIDE_EFFECT_FIELDS = ("issuance_status",)


class UndoOut(BaseModel):
    record_id: int
    field: str                      # 主要還原的欄位（顯示用）
    previous_value: str | None      # 還原前該主欄位的值
    restored_value: str | None      # 還原後該主欄位的值
    also_reverted: list[str] = []   # 一同還原的副作用欄位（譬如 issuance_status）
    record: RecordOut


@router.post("/undo", response_model=UndoOut)
def undo_last_edit(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """還原本人 UNDO_WINDOW_MINUTES 分鐘內最近一筆 record 編輯。
    同一 transaction 內寫進去的多筆 audit_log（共享 changed_at）會一起回滾，
    避免「主動作」與「副作用」拆開造成資料不一致。"""
    threshold = datetime.now() - timedelta(minutes=UNDO_WINDOW_MINUTES)

    primary = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user.id)
        .filter(AuditLog.changed_at >= threshold)
        .filter(~AuditLog.field_name.in_(SYSTEM_AUDIT_FIELDS + SIDE_EFFECT_FIELDS))
        .filter(~AuditLog.field_name.like("__undone__:%"))
        .order_by(AuditLog.id.desc())
        .first()
    )
    if not primary:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"{UNDO_WINDOW_MINUTES} 分鐘內沒有可還原的修改",
        )

    rec = db.query(Record).filter(Record.id == primary.record_id).first()
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "對應 record 已不存在")

    permitted = allowed_fields(user.role, rec.category_code)
    if user.role != "admin" and primary.field_name not in permitted:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"目前角色 {user.role} 已無權還原 {primary.field_name}",
        )

    # 同 transaction 內的同伴：相同 (user_id, record_id)，changed_at 在 ±1 秒內
    # （ORM 的 datetime.utcnow default 是 row-level，多筆會差幾微秒，不能用嚴格相等）
    window = timedelta(seconds=1)
    group = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user.id)
        .filter(AuditLog.record_id == primary.record_id)
        .filter(AuditLog.changed_at >= primary.changed_at - window)
        .filter(AuditLog.changed_at <= primary.changed_at + window)
        .filter(~AuditLog.field_name.in_(SYSTEM_AUDIT_FIELDS))
        .filter(~AuditLog.field_name.like("__undone__:%"))
        .all()
    )

    previous_main = _get_field(rec, primary.field_name)
    restored_main = (
        _coerce(primary.field_name, primary.old_value)
        if primary.old_value not in (None, "") else None
    )
    also: list[str] = []
    for entry in group:
        restored_val = (
            _coerce(entry.field_name, entry.old_value)
            if entry.old_value not in (None, "") else None
        )
        _set_field(rec, entry.field_name, restored_val)
        if entry.id != primary.id:
            also.append(entry.field_name)
        db.delete(entry)

    rec.updated_by = user.id
    rec.updated_at = datetime.utcnow()
    db.add(AuditLog(
        record_id=rec.id,
        user_id=user.id,
        field_name=f"__undone__:{primary.field_name}",
        old_value=str(previous_main) if previous_main is not None else None,
        new_value=str(restored_main) if restored_main is not None else None,
    ))
    db.commit()
    db.refresh(rec)

    return UndoOut(
        record_id=rec.id,
        field=primary.field_name,
        previous_value=str(previous_main) if previous_main is not None else None,
        restored_value=str(restored_main) if restored_main is not None else None,
        also_reverted=also,
        record=RecordOut.model_validate(rec, from_attributes=True),
    )


@router.patch("/{record_id}", response_model=RecordOut)
def patch_record(
    record_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec or rec.deleted_at is not None:
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
        old_val = _get_field(rec, field)
        if old_val == new_val:
            continue
        _set_field(rec, field, new_val)
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


class DeleteResult(BaseModel):
    id: int
    deleted: bool


@router.delete("/{record_id}", response_model=DeleteResult)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """軟刪除：標記 deleted_at，資料保留可還原。承辦限自己負責的類型，admin 全部。"""
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到 record")
    if not can_delete(user.role, rec.category_code):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "無刪除權限")
    if rec.deleted_at is not None:
        return DeleteResult(id=rec.id, deleted=True)  # 已是刪除狀態，idempotent

    rec.deleted_at = datetime.utcnow()
    rec.deleted_by = user.id
    db.add(AuditLog(
        record_id=rec.id,
        user_id=user.id,
        field_name="__deleted__",
        old_value=None,
        new_value=rec.category_code,
    ))
    db.commit()
    return DeleteResult(id=rec.id, deleted=True)


@router.post("/{record_id}/restore", response_model=RecordOut)
def restore_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """還原軟刪除的紀錄。權限同刪除。"""
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到 record")
    if not can_delete(user.role, rec.category_code):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "無還原權限")
    if rec.deleted_at is None:
        return rec  # 本來就沒刪，idempotent

    rec.deleted_at = None
    rec.deleted_by = None
    db.add(AuditLog(
        record_id=rec.id,
        user_id=user.id,
        field_name="__restored__",
        old_value=None,
        new_value=rec.category_code,
    ))
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/deleted", response_model=list[RecordOut])
def list_deleted(
    category_code: str = Query(..., description="category code"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出該類型已軟刪除的紀錄，供還原。權限同刪除。"""
    if not can_delete(user.role, category_code):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "無檢視已刪除權限")
    return (
        db.query(Record)
        .filter(Record.category_code == category_code)
        .filter(Record.deleted_at.isnot(None))
        .order_by(Record.deleted_at.desc())
        .all()
    )
