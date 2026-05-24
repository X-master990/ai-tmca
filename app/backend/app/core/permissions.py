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

# 類型專屬欄位（存在 extra JSONB），以 "extra.<key>" 表示。
# 各類型對應見 IMPORT-MAPPING.md。沒列出的類型（電腦伴唱機家族、自助KTV、
# 交通運輸工具）所有欄位都落在標準欄位，無 extra。
EXTRA_FIELDS_BY_CATEGORY: dict[str, set[str]] = {
    # §7 單場次表演
    "SINGLE_EVENT": {
        "extra.holder_tax_id", "extra.event_name", "extra.songs", "extra.song_count",
        "extra.venue", "extra.venue_address", "extra.audience_size",
        "extra.contact_org", "extra.contact_title", "extra.contact_email",
    },
    # §5 街頭藝人
    "STREET_ARTIST": {
        "extra.email", "extra.cert_issuer", "extra.street_cert_no", "extra.street_cert_expiry",
    },
    # §8 公開傳輸
    "PUBLIC_TRANSMIT": {
        "extra.email", "extra.has_revenue", "extra.platform_name",
        "extra.platform_url", "extra.songs",
    },
    # §9 告別式
    "FUNERAL": {
        "extra.ceremony_name", "extra.songs", "extra.language", "extra.song_count",
        "extra.venue", "extra.funeral_company", "extra.contact_email",
    },
    # §10 坪數-顯示器
    "AREA_DISPLAY": {
        "extra.applicant_ext", "extra.email", "extra.event_name",
        "extra.floor_area", "extra.songs", "extra.language",
    },
    # §11 大廳-宴會廳-客房
    "HALL_ROOM": {
        "extra.applicant_ext", "extra.email", "extra.floor_area",
    },
    # §12 競選活動
    "ELECTION": {
        "extra.holder_tax_id", "extra.event_name", "extra.venue", "extra.venue_address",
        "extra.songs", "extra.language", "extra.song_count",
        "extra.contact_org", "extra.contact_title", "extra.contact_email",
    },
}


def allowed_fields(role: str, category_code: str) -> set[str]:
    """回傳該 role 在該 category 可編輯的欄位集合。空集合 = 無編輯權。
    擁有全欄位權的角色，連帶取得該類型的 extra 專屬欄位。"""
    extra = EXTRA_FIELDS_BY_CATEGORY.get(category_code, set())
    if role == "admin":
        return ALL_EDITABLE_FIELDS | extra
    if role == "officer_a":
        return (ALL_EDITABLE_FIELDS | extra) if category_code == "SINGLE_EVENT" else set()
    if role == "officer_b":
        return (ALL_EDITABLE_FIELDS | extra) if category_code != "SINGLE_EVENT" else set()
    if role == "accountant":
        return INVOICE_FIELDS
    if role == "issuer":
        return ALL_EDITABLE_FIELDS | extra
    return set()  # viewer / 其他


def can_delete(role: str, category_code: str) -> bool:
    """誰能（軟）刪除該類型的紀錄：admin 全部；承辦限自己負責的類型。
    會計 / 核發 / viewer 不可刪。"""
    if role == "admin":
        return True
    if role == "officer_a":
        return category_code == "SINGLE_EVENT"
    if role == "officer_b":
        return category_code != "SINGLE_EVENT"
    return False
