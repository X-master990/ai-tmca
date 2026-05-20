"""角色 × 欄位白名單 unit tests"""
import pytest

from app.core.permissions import ALL_EDITABLE_FIELDS, INVOICE_FIELDS, allowed_fields


class TestAdmin:
    def test_admin_can_edit_all_categories(self):
        for cat in ["SINGLE_EVENT", "COMPUTER_KARAOKE", "RESTAURANT", "HOTEL"]:
            assert allowed_fields("admin", cat) == ALL_EDITABLE_FIELDS


class TestOfficerA:
    def test_officer_a_owns_single_event(self):
        # SINGLE_EVENT 是 officer_a 的地盤
        assert allowed_fields("officer_a", "SINGLE_EVENT") == ALL_EDITABLE_FIELDS

    def test_officer_a_blocked_on_other_categories(self):
        for cat in ["COMPUTER_KARAOKE", "RESTAURANT", "KTV"]:
            assert allowed_fields("officer_a", cat) == set()


class TestOfficerB:
    def test_officer_b_handles_non_single_event(self):
        for cat in ["COMPUTER_KARAOKE", "RESTAURANT", "KTV"]:
            assert allowed_fields("officer_b", cat) == ALL_EDITABLE_FIELDS

    def test_officer_b_blocked_on_single_event(self):
        assert allowed_fields("officer_b", "SINGLE_EVENT") == set()


class TestAccountant:
    def test_accountant_can_only_edit_invoice_fields(self):
        assert allowed_fields("accountant", "SINGLE_EVENT") == INVOICE_FIELDS

    def test_accountant_scope_is_consistent_across_categories(self):
        # 會計權限不分 category
        for cat in ["SINGLE_EVENT", "COMPUTER_KARAOKE", "RESTAURANT"]:
            assert allowed_fields("accountant", cat) == INVOICE_FIELDS

    def test_accountant_cannot_edit_use_address(self):
        assert "use_address" not in allowed_fields("accountant", "SINGLE_EVENT")

    def test_accountant_cannot_edit_holder_name(self):
        assert "holder_name" not in allowed_fields("accountant", "SINGLE_EVENT")

    @pytest.mark.parametrize("field", sorted(INVOICE_FIELDS))
    def test_accountant_can_edit_each_invoice_field(self, field):
        assert field in allowed_fields("accountant", "SINGLE_EVENT")


class TestIssuer:
    def test_issuer_can_edit_all_fields(self):
        assert allowed_fields("issuer", "SINGLE_EVENT") == ALL_EDITABLE_FIELDS

    def test_issuer_scope_consistent_across_categories(self):
        for cat in ["SINGLE_EVENT", "COMPUTER_KARAOKE"]:
            assert allowed_fields("issuer", cat) == ALL_EDITABLE_FIELDS

    def test_issuer_can_edit_amount(self):
        assert "amount" in allowed_fields("issuer", "SINGLE_EVENT")


class TestViewerAndUnknown:
    def test_viewer_writes_nothing(self):
        assert allowed_fields("viewer", "SINGLE_EVENT") == set()

    def test_unknown_role_writes_nothing(self):
        assert allowed_fields("hacker", "SINGLE_EVENT") == set()
        assert allowed_fields("", "SINGLE_EVENT") == set()


class TestInvariants:
    def test_invoice_fields_subset_of_all(self):
        # 發票欄位必須是全欄位的子集，否則 accountant 可能寫入不存在欄位
        assert INVOICE_FIELDS.issubset(ALL_EDITABLE_FIELDS)

    def test_invoice_no_in_invoice_fields(self):
        assert "invoice_no" in INVOICE_FIELDS
