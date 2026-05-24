"""records 客戶編號 customer_no（7碼：1碼類別前綴 + 6碼流水）

Revision ID: 008
Revises: 007
Create Date: 2026-05-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("records", sa.Column("customer_no", sa.String(7), nullable=True))
    op.create_index("ix_records_customer_no", "records", ["customer_no"])


def downgrade() -> None:
    op.drop_index("ix_records_customer_no", table_name="records")
    op.drop_column("records", "customer_no")
