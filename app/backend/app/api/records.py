"""Records API"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Category, Record, User
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
        .order_by(Record.issued_date.desc().nulls_last(), Record.id.desc())
        .all()
    )
    return rows
