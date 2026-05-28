"""Search API integration tests — 全欄位搜尋 + 代辦人交叉"""
import pytest


@pytest.fixture()
def search_seeds(make_record):
    return [
        make_record(
            category_code="SINGLE_EVENT",
            holder_name="玉亭演唱會",
            applicant_name="陳代辦",
            tax_id="11111111",
            cert_no="CERT-0001",
            invoice_no="INV-A001",
        ),
        make_record(
            category_code="SELF_SERVICE_KTV",
            holder_name="玉亭KTV",
            applicant_name="陳代辦",
            tax_id="22222222",
            cert_no="CERT-0002",
            invoice_no="INV-B002",
        ),
        make_record(
            category_code="SELF_SERVICE_KTV",
            holder_name="另一家KTV",
            applicant_name="王代辦",
            tax_id="33333333",
            cert_no="CERT-0003",
        ),
    ]


class TestSearch:
    def test_holder_name_match(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search?q=玉亭")
        assert r.status_code == 200
        body = r.json()
        names = [x["holder_name"] for x in body["results"]]
        assert any("玉亭" in n for n in names)
        assert body["total"] >= 2

    def test_cert_no_match(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search?q=CERT-0001")
        assert r.status_code == 200
        certs = [x["cert_no"] for x in r.json()["results"]]
        assert "CERT-0001" in certs

    def test_invoice_no_match(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search?q=INV-A001")
        body = r.json()
        invs = [x["invoice_no"] for x in body["results"]]
        assert "INV-A001" in invs

    def test_tax_id_match(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search?q=22222222")
        assert r.status_code == 200
        ids = [x["tax_id"] for x in r.json()["results"]]
        assert "22222222" in ids

    def test_category_filter(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search?q=玉亭&category_code=SELF_SERVICE_KTV")
        for item in r.json()["results"]:
            assert item["category_code"] == "SELF_SERVICE_KTV"

    def test_by_category_breakdown(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search?q=玉亭")
        bc = r.json()["by_category"]
        # 玉亭演唱會 + 玉亭KTV → 兩個 category 各 1
        assert bc.get("SINGLE_EVENT") == 1
        assert bc.get("SELF_SERVICE_KTV") == 1

    def test_no_match_returns_empty(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search?q=絕對找不到的字串zzzz")
        body = r.json()
        assert body["total"] == 0
        assert body["results"] == []

    def test_requires_auth(self, client):
        r = client.get("/api/search?q=anything")
        assert r.status_code == 401

    def test_blank_q_rejected(self, client_as_admin):
        r = client_as_admin.get("/api/search?q=")
        assert r.status_code == 422


class TestSearchAgents:
    def test_agent_lists_multiple_holders(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search/agents?name=陳代辦")
        assert r.status_code == 200
        body = r.json()
        # 陳代辦代辦 2 家公司
        assert body["distinct_holders"] == 2
        assert len(body["groups"]) == 2

    def test_agent_groups_have_categories(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search/agents?name=陳代辦")
        body = r.json()
        all_cats = {c for g in body["groups"] for c in g["categories"]}
        assert "SINGLE_EVENT" in all_cats
        assert "SELF_SERVICE_KTV" in all_cats

    def test_partial_name_match(self, client_as_admin, search_seeds):
        # 部分字元也應該命中（ilike %...%）
        r = client_as_admin.get("/api/search/agents?name=代辦")
        body = r.json()
        # 兩個代辦人都命中
        assert body["total_records"] == 3

    def test_unknown_agent_empty(self, client_as_admin, search_seeds):
        r = client_as_admin.get("/api/search/agents?name=完全不存在的代辦zzzz")
        body = r.json()
        assert body["total_records"] == 0
        assert body["groups"] == []

    def test_requires_auth(self, client):
        r = client.get("/api/search/agents?name=x")
        assert r.status_code == 401
