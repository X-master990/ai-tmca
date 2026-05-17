"""Category schemas"""
from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name_zh: str
    sheet_name: str | None
    assigned_role: str
    sort_order: int | None
    record_count: int = 0
