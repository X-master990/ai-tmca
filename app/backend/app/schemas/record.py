"""Record schemas"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_code: str

    cert_no: str | None
    issued_date: date | None
    note: str | None

    invoice_date: date | None
    invoice_type: str | None
    invoice_title: str | None
    tax_id: str | None
    invoice_no: str | None
    amount: int | None

    source: str | None
    officer: str | None
    action_type: str | None
    apply_date: date | None

    applicant_name: str | None
    applicant_id: str | None
    applicant_mobile: str | None
    applicant_phone: str | None
    applicant_fax: str | None

    holder_name: str | None
    holder_type: str | None

    use_zip: str | None
    use_address: str | None

    onsite_name: str | None
    onsite_mobile: str | None
    onsite_phone: str | None
    onsite_ext: str | None
    onsite_fax: str | None

    qty: int | None
    brand: str | None
    serial_no: str | None

    period_start: date | None
    period_end: date | None

    mail_type: str | None
    mail_zip: str | None
    mail_address: str | None
    mail_recipient: str | None
    mail_phone: str | None

    paper_application: bool
    paper_remittance: bool
    paper_official_doc: bool

    issuance_status: str
    renewal_status: str | None

    extra: dict

    created_at: datetime
    updated_at: datetime
