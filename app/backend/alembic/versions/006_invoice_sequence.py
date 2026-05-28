"""invoice_sequence 表 — 給發票自動編號

Revision ID: 006
Revises: 005
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoice_sequence",
        sa.Column("prefix", sa.String(8), primary_key=True),
        sa.Column("next_no", sa.BigInteger(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    # 預設 TU 起跳號碼來自會計現有模板的 設置!C2
    op.execute("INSERT INTO invoice_sequence (prefix, next_no) VALUES ('TU', 18164250)")


def downgrade() -> None:
    op.drop_table("invoice_sequence")
