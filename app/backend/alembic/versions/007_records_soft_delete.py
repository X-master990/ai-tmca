"""records 軟刪除欄位 — deleted_at / deleted_by

Revision ID: 007
Revises: 006
Create Date: 2026-05-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("records", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("records", sa.Column("deleted_by", sa.Integer(), nullable=True))
    # 列表查詢常以 deleted_at IS NULL 過濾，加部分索引加速「未刪除」掃描
    op.create_index(
        "ix_records_not_deleted",
        "records",
        ["category_code"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_records_not_deleted", table_name="records")
    op.drop_column("records", "deleted_by")
    op.drop_column("records", "deleted_at")
