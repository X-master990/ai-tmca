"""Renewals API — 續約偵測重算 + 月份清單 + 一鍵生成續約行 + 續約函生成"""
from datetime import date, datetime, timedelta
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.permissions import can_delete
from app.database import get_db
from app.models import AuditLog, Record, User
from app.schemas.record import RecordOut
from app.services.customer_no import assign_for_record
from app.services.renewal_letter import build_prefill, render_letter
from app.services.renewals import compute_renewal_status

router = APIRouter(prefix="/api/renewals", tags=["renewals"])

DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
LETTER_ROLES = ("officer_a", "officer_b", "admin")

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

    # 未續約 = 該月到期且尚未被續約（非綠）。紅(即將到期)與灰(尚未續約)都算未續約，
    # 與 30 天紅燈窗口無關 — 否則本月以外的月份名單會全空。
    renewed = [RecordOut.model_validate(r) for r in rows if r.renewal_status == "綠"]
    unrenewed = [RecordOut.model_validate(r) for r in rows if r.renewal_status != "綠"]
    other: list[RecordOut] = []  # 灰已併入未續約；保留鍵以相容前端

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


# ────────────────────────────────────────────────────────────────
# 續約函（電腦伴唱機）— 預填表單資料 + 產生 Word(.docx)
# ────────────────────────────────────────────────────────────────
class LetterData(BaseModel):
    """續約函表單預填值（前端 modal 帶入後可逐欄修改）。"""
    record_id: int
    recipient: str
    issue_date: str
    pay_deadline: str
    period_start: str
    period_end: str
    business_address: str
    qty: int
    amount: int


class LetterReq(BaseModel):
    """產生續約函的請求 — 所見即所印，前端送什麼就印什麼。

    各欄加長度上限：防禦性地擋掉異常大輸入（單請求放大成超大 docx）。
    """
    recipient: str = Field("", max_length=500)
    issue_date: str = Field("", max_length=60)
    pay_deadline: str = Field("", max_length=60)
    period_start: str = Field("", max_length=60)
    period_end: str = Field("", max_length=60)
    business_address: str = Field("", max_length=500)
    qty: str = Field("", max_length=40)
    amount: str = Field("", max_length=40)
    record_id: int | None = None  # 僅供稽核 / 命名，產檔不依賴它


@router.get("/{record_id}/letter-data", response_model=LetterData)
def renewal_letter_data(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*LETTER_ROLES)),
):
    """回某筆續約函的表單預填值（受文者/期間/地址/台數/金額/發文日/繳費期限）。"""
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec or rec.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到紀錄")
    return build_prefill(rec)


@router.post("/letter")
def renewal_letter(
    body: LetterReq,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*LETTER_ROLES)),
):
    """以表單內容填模板，回傳續約函 .docx（不改動總表資料；有 record_id 則留稽核）。"""
    try:
        docx_bytes = render_letter(body.model_dump())
    except FileNotFoundError:
        # 模板未部署到 /var/tmca/templates（例：未隨映像打包）→ 回乾淨訊息，不外洩路徑
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "續約函模板尚未就緒，請聯絡管理員",
        )

    if body.record_id is not None:
        # 與 letter-data 一致：略過軟刪除紀錄，不為已刪除/不存在者留稽核
        rec = (
            db.query(Record)
            .filter(Record.id == body.record_id, Record.deleted_at.is_(None))
            .first()
        )
        if rec is not None:
            db.add(AuditLog(
                record_id=rec.id,
                user_id=user.id,
                field_name="__renewal_letter__",
                old_value=None,
                new_value=(body.recipient or "")[:200],
            ))
            db.commit()

    stem = (body.recipient or (str(body.record_id) if body.record_id else "續約函")).strip()
    fname = f"續約函_{stem}_{date.today():%Y%m%d}.docx"
    # safe=''：'/' 等字元一併百分比編碼，符合 RFC 5987（店名含 '/' 時檔名不被截斷）
    cd = f"attachment; filename=renewal_letter.docx; filename*=UTF-8''{quote(fname, safe='')}"
    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type=DOCX_MEDIA,
        headers={"Content-Disposition": cd},
    )
