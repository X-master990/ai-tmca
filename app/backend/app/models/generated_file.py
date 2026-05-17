"""已產出檔案紀錄"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GeneratedFile(Base):
    __tablename__ = "generated_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("records.id"), index=True)
    template_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("templates.id"))
    file_path: Mapped[str] = mapped_column(String(400), nullable=False)
    generated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
