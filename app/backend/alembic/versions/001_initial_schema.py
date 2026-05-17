"""initial schema — users / categories / records / templates / generated_files / audit_log

Revision ID: 001
Revises:
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============ users ============
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(40), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(120), nullable=False),
        sa.Column("display_name", sa.String(40)),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime()),
        sa.CheckConstraint(
            "role IN ('officer_a','officer_b','accountant','issuer','viewer','admin')",
            name="users_role_check",
        ),
    )
    op.create_index("ix_users_username", "users", ["username"])

    # ============ categories ============
    op.create_table(
        "categories",
        sa.Column("code", sa.String(40), primary_key=True),
        sa.Column("name_zh", sa.String(40), nullable=False),
        sa.Column("sheet_name", sa.String(40)),
        sa.Column("assigned_role", sa.String(20), nullable=False),
        sa.Column("sort_order", sa.Integer()),
    )

    # ============ records ============
    op.create_table(
        "records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_code", sa.String(40), sa.ForeignKey("categories.code"), nullable=False),
        sa.Column("cert_no", sa.String(40), unique=True),
        sa.Column("issued_date", sa.Date()),
        sa.Column("note", sa.Text()),
        sa.Column("invoice_date", sa.Date()),
        sa.Column("invoice_type", sa.String(20)),
        sa.Column("invoice_title", sa.String(200)),
        sa.Column("tax_id", sa.String(20)),
        sa.Column("invoice_no", sa.String(40)),
        sa.Column("amount", sa.Integer()),
        sa.Column("source", sa.String(20)),
        sa.Column("officer", sa.String(40)),
        sa.Column("action_type", sa.String(20)),
        sa.Column("apply_date", sa.Date()),
        sa.Column("applicant_name", sa.String(80)),
        sa.Column("applicant_id", sa.String(20)),
        sa.Column("applicant_mobile", sa.String(30)),
        sa.Column("applicant_phone", sa.String(30)),
        sa.Column("applicant_fax", sa.String(30)),
        sa.Column("holder_name", sa.String(120)),
        sa.Column("holder_type", sa.String(40)),
        sa.Column("use_zip", sa.String(10)),
        sa.Column("use_address", sa.Text()),
        sa.Column("onsite_name", sa.String(40)),
        sa.Column("onsite_mobile", sa.String(30)),
        sa.Column("onsite_phone", sa.String(30)),
        sa.Column("onsite_ext", sa.String(20)),
        sa.Column("onsite_fax", sa.String(30)),
        sa.Column("qty", sa.Integer()),
        sa.Column("brand", sa.String(80)),
        sa.Column("serial_no", sa.String(400)),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.Column("mail_type", sa.String(10)),
        sa.Column("mail_zip", sa.String(10)),
        sa.Column("mail_address", sa.Text()),
        sa.Column("mail_recipient", sa.String(80)),
        sa.Column("mail_phone", sa.String(30)),
        sa.Column("paper_application", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("paper_remittance", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("paper_official_doc", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("issuance_status", sa.String(10), server_default="紅"),
        sa.Column("renewal_status", sa.String(10)),
        sa.Column("extra", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.CheckConstraint(
            "action_type IS NULL OR action_type IN ('新申辦','續約','授權延長','補發','其他')",
            name="records_action_type_check",
        ),
        sa.CheckConstraint(
            "mail_type IS NULL OR mail_type IN ('掛號','平信')",
            name="records_mail_type_check",
        ),
        sa.CheckConstraint(
            "issuance_status IN ('紅','綠')",
            name="records_issuance_status_check",
        ),
        sa.CheckConstraint(
            "renewal_status IS NULL OR renewal_status IN ('紅','綠','灰')",
            name="records_renewal_status_check",
        ),
    )
    op.create_index("ix_records_category_code", "records", ["category_code"])
    op.create_index("ix_records_holder_name", "records", ["holder_name"])
    op.create_index("ix_records_tax_id", "records", ["tax_id"])
    op.create_index("ix_records_period_end", "records", ["period_end"])
    op.create_index("ix_records_invoice_no", "records", ["invoice_no"])
    op.create_index("ix_records_applicant_name", "records", ["applicant_name"])
    op.create_index("ix_records_cert_no", "records", ["cert_no"])

    # 全文搜尋向量（generated column）
    op.execute("""
        ALTER TABLE records ADD COLUMN search_vec tsvector
        GENERATED ALWAYS AS (
            to_tsvector('simple',
                coalesce(cert_no,'') || ' ' ||
                coalesce(holder_name,'') || ' ' ||
                coalesce(applicant_name,'') || ' ' ||
                coalesce(tax_id,'') || ' ' ||
                coalesce(invoice_no,'') || ' ' ||
                coalesce(use_address,'') || ' ' ||
                coalesce(mail_address,'')
            )
        ) STORED
    """)
    op.execute("CREATE INDEX idx_records_search_vec ON records USING gin(search_vec)")

    # ============ templates ============
    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("category_code", sa.String(40), sa.ForeignKey("categories.code")),
        sa.Column("file_path", sa.String(400), nullable=False),
        sa.Column("field_mapping", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.CheckConstraint(
            "type IN ('cert_front','cert_back','envelope','notice')",
            name="templates_type_check",
        ),
    )

    # ============ generated_files ============
    op.create_table(
        "generated_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("record_id", sa.Integer(), sa.ForeignKey("records.id")),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("templates.id")),
        sa.Column("file_path", sa.String(400), nullable=False),
        sa.Column("generated_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("download_count", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_generated_files_record_id", "generated_files", ["record_id"])

    # ============ audit_log ============
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("record_id", sa.Integer(), sa.ForeignKey("records.id")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("field_name", sa.String(40), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("changed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_record", "audit_log", ["record_id", "changed_at"])

    # ============ Seed: 12 categories ============
    op.execute("""
        INSERT INTO categories (code, name_zh, sheet_name, assigned_role, sort_order) VALUES
        ('COMPUTER_KARAOKE',  '電腦伴唱機',         '電腦伴唱機',          'officer_b', 1),
        ('COMMUNITY_BOARD',   '社區管委會',         '社區管委會',          'officer_b', 2),
        ('PUBLIC_KARAOKE',    '公益伴唱機',         '公益伴唱機',          'officer_b', 3),
        ('SELF_SERVICE_KTV',  '自助KTV',            '自助KTV',             'officer_b', 4),
        ('STREET_ARTIST',     '街頭藝人',           '街頭藝人',            'officer_b', 5),
        ('TRANSPORT',         '交通運輸工具',       '交通運輸工具',        'officer_b', 6),
        ('SINGLE_EVENT',      '單場次表演',         '單場次表演',          'officer_a', 7),
        ('PUBLIC_TRANSMIT',   '公開傳輸',           '公開傳輸',            'officer_b', 8),
        ('FUNERAL',           '告別式',             '告別式',              'officer_b', 9),
        ('AREA_DISPLAY',      '坪數-顯示器',        '坪數-顯示器',         'officer_b', 10),
        ('HALL_ROOM',         '大廳-宴會廳-客房',   '大廳-宴會廳-客房',    'officer_b', 11),
        ('ELECTION',          '競選活動',           '競選活動',            'officer_b', 12)
    """)


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("generated_files")
    op.drop_table("templates")
    op.drop_table("records")
    op.drop_table("categories")
    op.drop_table("users")
