"""cert_no 移除 UNIQUE 約束 — 原始 Excel 有 77 個重複 cert_no（155 列），保留 index 但允許重複

Revision ID: 004
Revises: 003
Create Date: 2026-05-17
"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 原本 unique=True 會自動建一個 unique constraint，名稱通常是 records_cert_no_key
    op.drop_constraint("records_cert_no_key", "records", type_="unique")
    # 補回普通 index（如果不存在）
    op.create_index("ix_records_cert_no", "records", ["cert_no"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_records_cert_no", "records", if_exists=True)
    op.create_unique_constraint("records_cert_no_key", "records", ["cert_no"])
