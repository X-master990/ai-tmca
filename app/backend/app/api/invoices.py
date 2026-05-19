"""Invoices API — 開立發票（讀模板 + 配號 + 回 xlsx + 寫回 record）"""
from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import AuditLog, InvoiceSequence, Record, User
from app.services.invoices import CATEGORY_TO_PRODUCT, DEFAULT_PRODUCT, generate_invoice_xlsx

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

ROLES_CAN_ISSUE = {"admin", "accountant"}


class PendingInvoiceOut(BaseModel):
    """會計開立發票頁的精簡 schema — 對齊 Excel 模板的「明細」8 欄。"""
    id: int
    category_code: str
    holder_name: str | None
    invoice_type: str | None      # 發票型式
    invoice_title: str | None     # 抬頭
    tax_id: str | None            # 統一編號
    product: str                  # 品名（由 category 推導）
    amount: int | None            # 總金額（含稅）
    untaxed_unit_price: int       # 未稅單價 = round(amount / 1.05)
    note: str | None              # 備註


@router.get("/pending", response_model=list[PendingInvoiceOut])
def list_pending(
    category_code: str | None = Query(None, description="篩特定類型"),
    q: str | None = Query(None, description="模糊搜尋：抬頭/持證者/統編/備註"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出「金額>0 且 invoice_no IS NULL」的待開發票紀錄。"""
    if user.role not in ROLES_CAN_ISSUE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "無權限（僅 admin / accountant）")

    query = (
        db.query(Record)
        .filter(Record.invoice_no.is_(None))
        .filter(Record.amount.is_not(None))
        .filter(Record.amount > 0)
    )
    if category_code:
        query = query.filter(Record.category_code == category_code)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(
            Record.holder_name.ilike(like),
            Record.invoice_title.ilike(like),
            Record.tax_id.ilike(like),
            Record.note.ilike(like),
        ))

    rows = query.order_by(Record.id.desc()).limit(1000).all()
    out: list[PendingInvoiceOut] = []
    for r in rows:
        total = int(r.amount or 0)
        out.append(PendingInvoiceOut(
            id=r.id,
            category_code=r.category_code,
            holder_name=r.holder_name,
            invoice_type=r.invoice_type or "二聯式",
            invoice_title=r.invoice_title or r.holder_name,
            tax_id=r.tax_id,
            product=CATEGORY_TO_PRODUCT.get(r.category_code, DEFAULT_PRODUCT),
            amount=total,
            untaxed_unit_price=round(total / 1.05) if total else 0,
            note=r.note,
        ))
    return out


class GenerateReq(BaseModel):
    record_ids: list[int]
    issue_date: date | None = None
    invoice_type: str = "二聯式"
    prefix: str = "TU"


@router.get("/sequence")
def get_sequence(
    prefix: str = "TU",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    seq = db.query(InvoiceSequence).filter(InvoiceSequence.prefix == prefix).first()
    if not seq:
        raise HTTPException(404, f"找不到 prefix={prefix}")
    return {"prefix": seq.prefix, "next_no": seq.next_no}


@router.post("/generate")
def generate(
    body: GenerateReq,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ROLES_CAN_ISSUE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "無開立發票權限（僅 admin / accountant）")

    issue_date = body.issue_date or date.today()
    try:
        xlsx_bytes, assigned = generate_invoice_xlsx(
            db,
            record_ids=body.record_ids,
            issue_date=issue_date,
            invoice_type=body.invoice_type,
            prefix=body.prefix,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    # 寫回 record + audit
    for rid, inv_no in assigned:
        rec = db.query(Record).filter(Record.id == rid).first()
        if not rec:
            continue
        old_no = rec.invoice_no
        rec.invoice_no = inv_no
        rec.invoice_date = issue_date
        rec.invoice_type = body.invoice_type
        if rec.issuance_status != "綠":
            rec.issuance_status = "綠"
        db.add(AuditLog(
            record_id=rec.id,
            user_id=user.id,
            field_name="invoice_no",
            old_value=old_no,
            new_value=inv_no,
        ))

    db.commit()

    fname = f"invoice_{issue_date.isoformat()}_{len(assigned)}.xlsx"
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "X-Invoice-Count": str(len(assigned)),
            "X-Invoice-First": assigned[0][1] if assigned else "",
            "X-Invoice-Last": assigned[-1][1] if assigned else "",
        },
    )
