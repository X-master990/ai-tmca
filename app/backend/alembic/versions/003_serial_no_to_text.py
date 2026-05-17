"""serial_no String(400) → Text — 多機號用「、」串接會超過 400 字

Revision ID: 003
Revises: 002
Create Date: 2026-05-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("records", "serial_no", type_=sa.Text(), existing_type=sa.String(400))


def downgrade() -> None:
    op.alter_column("records", "serial_no", type_=sa.String(400), existing_type=sa.Text())
