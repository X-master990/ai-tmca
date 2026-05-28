"""Records PATCH 副作用：invoice_no ↔ issuance_status、audit_log 寫入"""
import pytest

from app.models import AuditLog


@pytest.fixture()
def red_rec(make_record):
    return make_record(
        category_code="SINGLE_EVENT",
        holder_name="A",
        invoice_no=None,
        issuance_status="紅",
    )


@pytest.fixture()
def green_rec(make_record):
    return make_record(
        category_code="SINGLE_EVENT",
        holder_name="B",
        invoice_no="TC12345678",
        issuance_status="綠",
    )


class TestInvoiceFlipsIssuance:
    def test_setting_invoice_no_flips_to_green(self, client_as_issuer, red_rec):
        assert red_rec.issuance_status == "紅"
        r = client_as_issuer.patch(
            f"/api/records/{red_rec.id}",
            json={"invoice_no": "AB12345678"},
        )
        assert r.status_code == 200
        assert r.json()["issuance_status"] == "綠"
        assert r.json()["invoice_no"] == "AB12345678"

    def test_no_change_when_invoice_no_unchanged(self, client_as_issuer, green_rec):
        r = client_as_issuer.patch(
            f"/api/records/{green_rec.id}",
            json={"invoice_no": "TC12345678"},
        )
        assert r.status_code == 200
        assert r.json()["issuance_status"] == "綠"

    @pytest.mark.xfail(
        reason="strategy 文件期望「清空 invoice_no → issuance_status 翻回紅」，"
               "但 records.py:129-134 只實作了單向翻綠。等決議要修哪邊。",
        strict=True,
    )
    def test_clearing_invoice_no_flips_back_to_red(self, client_as_issuer, green_rec):
        r = client_as_issuer.patch(
            f"/api/records/{green_rec.id}",
            json={"invoice_no": ""},
        )
        assert r.status_code == 200
        assert r.json()["issuance_status"] == "紅"


class TestAuditLog:
    def test_patch_writes_audit_row(self, client_as_admin, red_rec, db):
        r = client_as_admin.patch(
            f"/api/records/{red_rec.id}",
            json={"note": "新註記"},
        )
        assert r.status_code == 200
        logs = db.query(AuditLog).filter_by(record_id=red_rec.id, field_name="note").all()
        assert any(l.new_value == "新註記" for l in logs)

    def test_audit_log_records_old_and_new(self, client_as_admin, red_rec, db):
        client_as_admin.patch(f"/api/records/{red_rec.id}", json={"note": "first"})
        client_as_admin.patch(f"/api/records/{red_rec.id}", json={"note": "second"})
        logs = (
            db.query(AuditLog)
            .filter_by(record_id=red_rec.id, field_name="note")
            .order_by(AuditLog.id)
            .all()
        )
        assert len(logs) == 2
        assert logs[0].old_value is None and logs[0].new_value == "first"
        assert logs[1].old_value == "first" and logs[1].new_value == "second"

    def test_setting_invoice_no_logs_both_fields(self, client_as_issuer, red_rec, db):
        # 改 invoice_no 觸發 issuance_status 連動，兩條 audit log 都應被寫
        client_as_issuer.patch(
            f"/api/records/{red_rec.id}",
            json={"invoice_no": "XX99999999"},
        )
        fields = {
            l.field_name
            for l in db.query(AuditLog).filter_by(record_id=red_rec.id).all()
        }
        assert "invoice_no" in fields
        assert "issuance_status" in fields

    def test_audit_log_attributes_to_user(self, client_as_admin, red_rec, db):
        from app.models import User
        admin = db.query(User).filter_by(username="admin").first()
        client_as_admin.patch(f"/api/records/{red_rec.id}", json={"note": "test"})
        log = (
            db.query(AuditLog)
            .filter_by(record_id=red_rec.id, field_name="note")
            .first()
        )
        assert log.user_id == admin.id


class TestNoOpPatch:
    def test_same_value_no_audit_log(self, client_as_admin, red_rec, db):
        # PATCH 同樣的值 → 不應產生 audit log
        client_as_admin.patch(f"/api/records/{red_rec.id}", json={"note": "x"})
        # 第二次同值
        client_as_admin.patch(f"/api/records/{red_rec.id}", json={"note": "x"})
        logs = db.query(AuditLog).filter_by(record_id=red_rec.id, field_name="note").all()
        assert len(logs) == 1


class TestCoercion:
    def test_amount_string_coerced_to_int(self, client_as_accountant, red_rec):
        r = client_as_accountant.patch(
            f"/api/records/{red_rec.id}",
            json={"amount": "1350"},  # 前端可能傳字串
        )
        assert r.status_code == 200
        assert r.json()["amount"] == 1350

    def test_invalid_date_returns_400(self, client_as_admin, red_rec):
        r = client_as_admin.patch(
            f"/api/records/{red_rec.id}",
            json={"issued_date": "not-a-date"},
        )
        assert r.status_code == 400
        assert "issued_date" in r.json()["detail"]

    def test_iso_date_string_accepted(self, client_as_admin, red_rec):
        r = client_as_admin.patch(
            f"/api/records/{red_rec.id}",
            json={"issued_date": "2026-05-18"},
        )
        assert r.status_code == 200
        assert r.json()["issued_date"] == "2026-05-18"
