"""Categories API"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Category, Record, User
from app.schemas.category import CategoryOut

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """12 個 category + 每個 category 的 record 數量。"""
    counts = dict(
        db.query(Record.category_code, func.count(Record.id))
        .group_by(Record.category_code)
        .all()
    )
    cats = db.query(Category).order_by(Category.sort_order).all()
    return [
        CategoryOut(
            code=c.code,
            name_zh=c.name_zh,
            sheet_name=c.sheet_name,
            assigned_role=c.assigned_role,
            sort_order=c.sort_order,
            record_count=counts.get(c.code, 0),
        )
        for c in cats
    ]
