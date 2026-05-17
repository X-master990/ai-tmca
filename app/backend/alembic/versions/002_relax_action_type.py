"""relax action_type CHECK — 真實資料有 20+ 種值（新件/和解件/作廢/...），改為自由文字

Revision ID: 002
Revises: 001
Create Date: 2026-05-17
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("records_action_type_check", "records", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "records_action_type_check",
        "records",
        "action_type IS NULL OR action_type IN ('新申辦','續約','授權延長','補發','其他')",
    )
