"""角色 × 欄位 編輯權限矩陣"""

# 通用發票/金額欄位
INVOICE_FIELDS = {"invoice_date", "invoice_type", "invoice_title", "tax_id", "invoice_no", "amount"}

# 全欄位白名單（不含系統欄如 id / category_code / created_at / updated_at / *_status / extra）
ALL_EDITABLE_FIELDS = {
    "cert_no", "issued_date", "note",
    "invoice_date", "invoice_type", "invoice_title", "tax_id", "invoice_no", "amount",
    "source", "officer", "action_type", "apply_date",
    "applicant_name", "applicant_id", "applicant_mobile", "applicant_phone", "applicant_fax",
    "holder_name", "holder_type",
    "use_zip", "use_address",
    "onsite_name", "onsite_mobile", "onsite_phone", "onsite_ext", "onsite_fax",
    "qty", "brand", "serial_no",
    "period_start", "period_end",
    "mail_type", "mail_zip", "mail_address", "mail_recipient", "mail_phone",
    "paper_application", "paper_remittance", "paper_official_doc",
    "issuance_status", "renewal_status",
}


def allowed_fields(role: str, category_code: str) -> set[str]:
    """回傳該 role 在該 category 可編輯的欄位集合。空集合 = 無編輯權。"""
    if role == "admin":
        return ALL_EDITABLE_FIELDS
    if role == "officer_a":
        return ALL_EDITABLE_FIELDS if category_code == "SINGLE_EVENT" else set()
    if role == "officer_b":
        return ALL_EDITABLE_FIELDS if category_code != "SINGLE_EVENT" else set()
    if role == "accountant":
        return INVOICE_FIELDS
    if role == "issuer":
        return ALL_EDITABLE_FIELDS
    return set()  # viewer / 其他
