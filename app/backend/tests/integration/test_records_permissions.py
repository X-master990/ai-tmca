"""Records 角色 × 欄位白名單 integration tests"""
import pytest


@pytest.fixture()
def single_event_rec(make_record):
    return make_record(
        category_code="SINGLE_EVENT",
        holder_name="A 演唱會",
        use_address="原地址",
        invoice_no=None,
    )


@pytest.fixture()
def ktv_rec(make_record):
    return make_record(
        category_code="SELF_SERVICE_KTV",
        holder_name="KTV 店",
        use_address="原地址",
    )


class TestOfficerAOnSingleEvent:
    def test_can_edit_use_address(self, client_as_officer_a, single_event_rec):
        r = client_as_officer_a.patch(
            f"/api/records/{single_event_rec.id}",
            json={"use_address": "改的地址"},
        )
        assert r.status_code == 200
        assert r.json()["use_address"] == "改的地址"

    def test_can_edit_holder_name(self, client_as_officer_a, single_event_rec):
        r = client_as_officer_a.patch(
            f"/api/records/{single_event_rec.id}",
            json={"holder_name": "B 演唱會"},
        )
        assert r.status_code == 200
        assert r.json()["holder_name"] == "B 演唱會"


class TestOfficerABlockedOnOther:
    def test_cannot_edit_ktv(self, client_as_officer_a, ktv_rec):
        r = client_as_officer_a.patch(
            f"/api/records/{ktv_rec.id}",
            json={"note": "改"},
        )
        assert r.status_code == 403


class TestOfficerBOnKtv:
    def test_can_edit_ktv(self, client_as_officer_b, ktv_rec):
        r = client_as_officer_b.patch(
            f"/api/records/{ktv_rec.id}",
            json={"note": "好"},
        )
        assert r.status_code == 200

    def test_cannot_edit_single_event(self, client_as_officer_b, single_event_rec):
        r = client_as_officer_b.patch(
            f"/api/records/{single_event_rec.id}",
            json={"note": "改"},
        )
        assert r.status_code == 403


class TestAccountant:
    def test_can_edit_invoice_no(self, client_as_accountant, single_event_rec):
        r = client_as_accountant.patch(
            f"/api/records/{single_event_rec.id}",
            json={"invoice_no": "TC99999999"},
        )
        assert r.status_code == 200
        assert r.json()["invoice_no"] == "TC99999999"

    def test_can_edit_amount(self, client_as_accountant, single_event_rec):
        r = client_as_accountant.patch(
            f"/api/records/{single_event_rec.id}",
            json={"amount": 1350},
        )
        assert r.status_code == 200
        assert r.json()["amount"] == 1350

    def test_cannot_edit_use_address(self, client_as_accountant, single_event_rec):
        r = client_as_accountant.patch(
            f"/api/records/{single_event_rec.id}",
            json={"use_address": "改的地址"},
        )
        assert r.status_code == 403
        assert "use_address" in r.json()["detail"]

    def test_cannot_edit_holder_name(self, client_as_accountant, single_event_rec):
        r = client_as_accountant.patch(
            f"/api/records/{single_event_rec.id}",
            json={"holder_name": "改"},
        )
        assert r.status_code == 403

    def test_works_across_categories(self, client_as_accountant, single_event_rec, ktv_rec):
        # 會計權限不分 category
        r1 = client_as_accountant.patch(
            f"/api/records/{single_event_rec.id}", json={"invoice_no": "A1"}
        )
        r2 = client_as_accountant.patch(
            f"/api/records/{ktv_rec.id}", json={"invoice_no": "B2"}
        )
        assert r1.status_code == 200
        assert r2.status_code == 200


class TestIssuer:
    def test_can_edit_invoice_no(self, client_as_issuer, single_event_rec):
        r = client_as_issuer.patch(
            f"/api/records/{single_event_rec.id}",
            json={"invoice_no": "TC12345678"},
        )
        assert r.status_code == 200

    def test_can_edit_amount(self, client_as_issuer, single_event_rec):
        r = client_as_issuer.patch(
            f"/api/records/{single_event_rec.id}",
            json={"amount": 999},
        )
        assert r.status_code == 200

    def test_can_edit_use_address_across_categories(self, client_as_issuer, single_event_rec, ktv_rec):
        r1 = client_as_issuer.patch(
            f"/api/records/{single_event_rec.id}", json={"use_address": "A"}
        )
        r2 = client_as_issuer.patch(
            f"/api/records/{ktv_rec.id}", json={"use_address": "B"}
        )
        assert r1.status_code == 200
        assert r2.status_code == 200


class TestAdmin:
    def test_admin_can_edit_anything(self, client_as_admin, single_event_rec, ktv_rec):
        r1 = client_as_admin.patch(
            f"/api/records/{single_event_rec.id}",
            json={"use_address": "新地址"},
        )
        r2 = client_as_admin.patch(
            f"/api/records/{ktv_rec.id}",
            json={"holder_name": "新持證者"},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200


class TestUnauthorized:
    def test_patch_without_auth(self, client, single_event_rec):
        r = client.patch(f"/api/records/{single_event_rec.id}", json={"note": "x"})
        assert r.status_code == 401

    def test_patch_unknown_record(self, client_as_admin):
        r = client_as_admin.patch("/api/records/999999", json={"note": "x"})
        assert r.status_code == 404


class TestCreate:
    def test_officer_a_creates_single_event(self, client_as_officer_a):
        r = client_as_officer_a.post("/api/records", json={
            "category_code": "SINGLE_EVENT",
            "holder_name": "新案演唱會",
            "tax_id": "99887766",
            "amount": 1350,
        })
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["category_code"] == "SINGLE_EVENT"
        assert body["holder_name"] == "新案演唱會"
        assert body["issuance_status"] == "紅"  # 沒填發票號 → 紅

    def test_officer_a_blocked_on_ktv(self, client_as_officer_a):
        r = client_as_officer_a.post("/api/records", json={
            "category_code": "SELF_SERVICE_KTV",
            "holder_name": "想偷加 KTV",
        })
        assert r.status_code == 403

    def test_officer_b_creates_ktv(self, client_as_officer_b):
        r = client_as_officer_b.post("/api/records", json={
            "category_code": "SELF_SERVICE_KTV",
            "holder_name": "新 KTV 店",
        })
        assert r.status_code == 201

    def test_accountant_cannot_create_anything(self, client_as_accountant):
        r = client_as_accountant.post("/api/records", json={
            "category_code": "SINGLE_EVENT",
            "holder_name": "x",
        })
        # accountant 只能寫 INVOICE_FIELDS，holder_name 不在 → 403
        assert r.status_code == 403

    def test_missing_category_400(self, client_as_admin):
        r = client_as_admin.post("/api/records", json={"holder_name": "x"})
        assert r.status_code == 400

    def test_unknown_category_400(self, client_as_admin):
        r = client_as_admin.post("/api/records", json={
            "category_code": "NOT_EXIST",
            "holder_name": "x",
        })
        assert r.status_code == 400

    def test_invoice_no_at_creation_flips_green(self, client_as_admin):
        r = client_as_admin.post("/api/records", json={
            "category_code": "SINGLE_EVENT",
            "holder_name": "已開發票案",
            "invoice_no": "TC00000001",
        })
        assert r.status_code == 201
        assert r.json()["issuance_status"] == "綠"


class TestPermissionsEndpoint:
    def test_accountant_sees_only_invoice_fields(self, client_as_accountant):
        r = client_as_accountant.get("/api/records/permissions")
        assert r.status_code == 200
        body = r.json()
        assert body["role"] == "accountant"
        # 12 categories 都應該存在、欄位只含發票相關
        for code, fields in body["editable_fields_by_category"].items():
            assert "use_address" not in fields
            assert "invoice_no" in fields

    def test_admin_sees_full_fields(self, client_as_admin):
        r = client_as_admin.get("/api/records/permissions")
        assert r.status_code == 200
        body = r.json()
        for code, fields in body["editable_fields_by_category"].items():
            assert "use_address" in fields
            assert "holder_name" in fields
