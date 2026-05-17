"""總表主表 records — 對應 SYSTEM-DESIGN.md §三 records DDL"""
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Record(Base):
    """總表主表 — 12 個申請類型共用，類型專屬欄位放在 extra JSONB"""
    __tablename__ = "records"
    __table_args__ = (
        CheckConstraint(
            "mail_type IS NULL OR mail_type IN ('掛號','平信')",
            name="records_mail_type_check",
        ),
        CheckConstraint(
            "issuance_status IN ('紅','綠')",
            name="records_issuance_status_check",
        ),
        CheckConstraint(
            "renewal_status IS NULL OR renewal_status IN ('紅','綠','灰')",
            name="records_renewal_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_code: Mapped[str] = mapped_column(
        String(40), ForeignKey("categories.code"), nullable=False, index=True
    )

    # 識別
    cert_no: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    issued_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)

    # 發票
    invoice_date: Mapped[date | None] = mapped_column(Date)
    invoice_type: Mapped[str | None] = mapped_column(String(20))
    invoice_title: Mapped[str | None] = mapped_column(String(200))
    tax_id: Mapped[str | None] = mapped_column(String(20), index=True)
    invoice_no: Mapped[str | None] = mapped_column(String(40), index=True)
    amount: Mapped[int | None] = mapped_column(Integer)

    # 承辦
    source: Mapped[str | None] = mapped_column(String(20))  # 提報：承辦 / 自辦
    officer: Mapped[str | None] = mapped_column(String(40))
    action_type: Mapped[str | None] = mapped_column(String(20))  # 辦理項目
    apply_date: Mapped[date | None] = mapped_column(Date)

    # 申請人
    applicant_name: Mapped[str | None] = mapped_column(String(80), index=True)
    applicant_id: Mapped[str | None] = mapped_column(String(20))
    applicant_mobile: Mapped[str | None] = mapped_column(String(30))
    applicant_phone: Mapped[str | None] = mapped_column(String(30))
    applicant_fax: Mapped[str | None] = mapped_column(String(30))

    # 持證者（續約比對關鍵）
    holder_name: Mapped[str | None] = mapped_column(String(120), index=True)
    holder_type: Mapped[str | None] = mapped_column(String(40))

    # 使用地址
    use_zip: Mapped[str | None] = mapped_column(String(10))
    use_address: Mapped[str | None] = mapped_column(Text)

    # 現場聯絡
    onsite_name: Mapped[str | None] = mapped_column(String(40))
    onsite_mobile: Mapped[str | None] = mapped_column(String(30))
    onsite_phone: Mapped[str | None] = mapped_column(String(30))
    onsite_ext: Mapped[str | None] = mapped_column(String(20))
    onsite_fax: Mapped[str | None] = mapped_column(String(30))

    # 標的
    qty: Mapped[int | None] = mapped_column(Integer)
    brand: Mapped[str | None] = mapped_column(String(80))
    serial_no: Mapped[str | None] = mapped_column(Text)

    # 授權期間（續約比對關鍵）
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date, index=True)

    # 寄證地址（含確認欄）
    mail_type: Mapped[str | None] = mapped_column(String(10))  # 掛號 / 平信
    mail_zip: Mapped[str | None] = mapped_column(String(10))
    mail_address: Mapped[str | None] = mapped_column(Text)
    mail_recipient: Mapped[str | None] = mapped_column(String(80))
    mail_phone: Mapped[str | None] = mapped_column(String(30))

    # 紙本收件確認（不上傳雲端，僅 checkbox）
    paper_application: Mapped[bool] = mapped_column(default=False)  # 已收申請書
    paper_remittance: Mapped[bool] = mapped_column(default=False)   # 已收匯款單/發票
    paper_official_doc: Mapped[bool] = mapped_column(default=False) # 已收申請內容公文

    # 系統狀態
    issuance_status: Mapped[str] = mapped_column(String(10), default="紅")
    renewal_status: Mapped[str | None] = mapped_column(String(10))

    # 類型專屬欄位（每個 category 可能有幾個獨特欄位放這裡）
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    # 稽核
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
