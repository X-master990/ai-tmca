"""一次拉寬所有易爆字串欄位，避免匯入打地鼠

Revision ID: 005
Revises: 004
Create Date: 2026-05-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 拉寬清單：(欄位, 新型態, 舊型態)
CHANGES = [
    ("invoice_type", sa.String(40), sa.String(20)),
    ("invoice_title", sa.Text(), sa.String(200)),
    ("tax_id", sa.String(40), sa.String(20)),
    ("source", sa.String(40), sa.String(20)),
    ("officer", sa.String(80), sa.String(40)),
    ("action_type", sa.String(40), sa.String(20)),
    ("applicant_name", sa.String(120), sa.String(80)),
    ("applicant_id", sa.String(40), sa.String(20)),
    ("applicant_mobile", sa.String(80), sa.String(30)),
    ("applicant_phone", sa.String(80), sa.String(30)),
    ("applicant_fax", sa.String(80), sa.String(30)),
    ("holder_name", sa.String(200), sa.String(120)),
    ("holder_type", sa.String(80), sa.String(40)),
    ("use_zip", sa.String(20), sa.String(10)),
    ("onsite_name", sa.String(80), sa.String(40)),
    ("onsite_mobile", sa.String(80), sa.String(30)),
    ("onsite_phone", sa.String(80), sa.String(30)),
    ("onsite_ext", sa.String(40), sa.String(20)),
    ("onsite_fax", sa.String(80), sa.String(30)),
    ("brand", sa.String(120), sa.String(80)),
    ("mail_type", sa.String(20), sa.String(10)),
    ("mail_zip", sa.String(20), sa.String(10)),
    ("mail_recipient", sa.String(120), sa.String(80)),
    ("mail_phone", sa.String(80), sa.String(30)),
]


def upgrade() -> None:
    for col, new_type, _ in CHANGES:
        op.alter_column("records", col, type_=new_type)


def downgrade() -> None:
    for col, _, old_type in CHANGES:
        op.alter_column("records", col, type_=old_type)
