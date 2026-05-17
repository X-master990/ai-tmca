"""Word 模板 metadata"""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = (
        CheckConstraint(
            "type IN ('cert_front','cert_back','envelope','notice')",
            name="templates_type_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    category_code: Mapped[str | None] = mapped_column(String(40), ForeignKey("categories.code"))
    file_path: Mapped[str] = mapped_column(String(400), nullable=False)
    field_mapping: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
