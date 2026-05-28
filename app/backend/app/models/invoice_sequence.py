"""發票序號 — 單列表，按 prefix 取下一個號碼"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InvoiceSequence(Base):
    __tablename__ = "invoice_sequence"

    prefix: Mapped[str] = mapped_column(String(8), primary_key=True)
    next_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
