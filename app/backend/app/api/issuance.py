"""核發 API — 待核發清單 + 產生證書(正面 Word) + 自動轉綠

僅 核發(issuer) / admin 可用。產證書不修改模板，預設產出後把該筆標記為已核發(綠)。
"""
from datetime import date, datetime
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.database import get_db
from app.models import AuditLog, Record, User
from app.services.cert import build_cert_prefill, has_cert, render_cert

router = APIRouter(prefix="/api/issuance", tags=["issuance"])

DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ISSUER_ROLES = ("issuer", "admin")
CERT_ISSUED_FIELD = "__cert_issued__"


class PendingIssuanceOut(BaseModel):
    """核發頁清單列 — 待核發(紅)紀錄精簡欄位。"""
    id: int
    category_code: str
    cert_no: str | None
    holder_name: str | None
    use_address: str | None
    period_start: date | None
    period_end: date | None
    qty: int | None
    issuance_status: str
    has_cert: bool  # 該類別是否有對應正面模板（無則前端不給產證書）


@router.get("/pending", response_model=list[PendingIssuanceOut])
def list_pending(
    category_code: str | None = Query(None),
    q: str | None = Query(None, description="模糊搜尋：持證者/證號/統編/地址"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*ISSUER_ROLES)),
):
    """列出待核發(issuance_status=紅、未軟刪)紀錄。"""
    query = (
        db.query(Record)
        .filter(Record.issuance_status == "紅")
        .filter(Record.deleted_at.is_(None))
    )
    if category_code:
        query = query.filter(Record.category_code == category_code)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(
            Record.holder_name.ilike(like),
            Record.cert_no.ilike(like),
            Record.tax_id.ilike(like),
            Record.use_address.ilike(like),
        ))
    rows = query.order_by(Record.id.desc()).limit(1000).all()
    return [
        PendingIssuanceOut(
            id=r.id,
            category_code=r.category_code,
            cert_no=r.cert_no,
            holder_name=r.holder_name,
            use_address=r.use_address,
            period_start=r.period_start,
            period_end=r.period_end,
            qty=r.qty,
            issuance_status=r.issuance_status,
            has_cert=has_cert(r.category_code),
        )
        for r in rows
    ]


class CertFieldOut(BaseModel):
    name: str
    value: str


class CertDataOut(BaseModel):
    record_id: int
    category_code: str
    template: str | None
    fields: list[CertFieldOut]


@router.get("/{record_id}/cert-data", response_model=CertDataOut)
def cert_data(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*ISSUER_ROLES)),
):
    """回某筆證書的表單預填值（依模板實際合併欄位逐欄帶入）。"""
    rec = (
        db.query(Record)
        .filter(Record.id == record_id, Record.deleted_at.is_(None))
        .first()
    )
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到紀錄")
    if not has_cert(rec.category_code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "此類別沒有對應的證書模板")
    pre = build_cert_prefill(rec)
    return CertDataOut(
        record_id=rec.id,
        category_code=rec.category_code,
        template=pre["template"],
        fields=[CertFieldOut(**f) for f in pre["fields"]],
    )


class CertReq(BaseModel):
    """產證書請求 — fields 為合併欄位名→值；所見即所印。"""
    fields: dict[str, str] = {}
    mark_issued: bool = True  # 產出後標記為已核發(綠)

    @field_validator("fields")
    @classmethod
    def _limit_size(cls, v: dict[str, str]) -> dict[str, str]:
        # 防禦：擋掉異常大的請求體（欄位數 / 單值長度）
        if len(v) > 50:
            raise ValueError("欄位數過多")
        for val in v.values():
            if isinstance(val, str) and len(val) > 2000:
                raise ValueError("欄位值過長")
        return v


@router.post("/{record_id}/cert")
def generate_cert(
    record_id: int,
    body: CertReq,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*ISSUER_ROLES)),
):
    """以表單內容填正面模板，回證書 .docx；預設把該筆標記為已核發(綠)並留稽核。"""
    rec = (
        db.query(Record)
        .filter(Record.id == record_id, Record.deleted_at.is_(None))
        .first()
    )
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到紀錄")
    if not has_cert(rec.category_code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "此類別沒有對應的證書模板")

    try:
        docx_bytes = render_cert(rec.category_code, body.fields)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "證書模板尚未就緒，請聯絡管理員")
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    # 自動轉綠（已核發）+ 稽核
    if body.mark_issued and rec.issuance_status != "綠":
        old = rec.issuance_status
        rec.issuance_status = "綠"
        rec.updated_by = user.id
        rec.updated_at = datetime.utcnow()
        db.add(AuditLog(
            record_id=rec.id, user_id=user.id,
            field_name="issuance_status", old_value=old, new_value="綠",
        ))
    db.add(AuditLog(
        record_id=rec.id, user_id=user.id,
        field_name=CERT_ISSUED_FIELD, old_value=None,
        new_value=(rec.cert_no or body.fields.get("證號") or body.fields.get("證書編號") or "")[:200],
    ))
    db.commit()

    stem = (rec.cert_no or rec.holder_name or str(rec.id)).strip()
    fname = f"證書_{stem}_{date.today():%Y%m%d}.docx"
    cd = f"attachment; filename=certificate.docx; filename*=UTF-8''{quote(fname, safe='')}"
    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type=DOCX_MEDIA,
        headers={"Content-Disposition": cd},
    )
