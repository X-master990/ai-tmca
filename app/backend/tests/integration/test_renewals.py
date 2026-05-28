"""Renewals API integration tests"""
from datetime import date, timedelta

import pytest


TODAY = date.today()


@pytest.fixture()
def renewable_pair(make_record, db):
    """同 holder 在同 category 下：一筆舊到期 + 一筆新到期 → 舊那筆會被標 '綠'。"""
    from app.services.renewals import compute_renewal_status

    old = make_record(
        category_code="SELF_SERVICE_KTV",
        holder_name="玉亭餐廳",
        tax_id="12345678",
        period_end=date(TODAY.year, 5, 14),
    )
    new = make_record(
        category_code="SELF_SERVICE_KTV",
        holder_name="玉亭餐廳",
        tax_id="12345678",
        period_end=date(TODAY.year + 1, 5, 14),
    )
    compute_renewal_status(db)
    db.refresh(old)
    db.refresh(new)
    return old, new


@pytest.fixture()
def lonely_red(make_record, db):
    """一筆 30 天內到期、且沒有續約 → '紅'"""
    from app.services.renewals import compute_renewal_status

    rec = make_record(
        category_code="SELF_SERVICE_KTV",
        holder_name="孤獨餐廳",
        tax_id="99999999",
        period_end=TODAY + timedelta(days=10),
    )
    compute_renewal_status(db)
    db.refresh(rec)
    return rec


class TestRecompute:
    def test_admin_can_recompute(self, client_as_admin):
        r = client_as_admin.post("/api/renewals/recompute")
        assert r.status_code == 200
        body = r.json()
        assert "rows_updated" in body
        assert "elapsed_seconds" in body
        assert "breakdown" in body

    def test_non_admin_blocked(self, client_as_officer_a):
        r = client_as_officer_a.post("/api/renewals/recompute")
        assert r.status_code == 403

    def test_anon_blocked(self, client):
        r = client.post("/api/renewals/recompute")
        assert r.status_code == 401


class TestRenewalStatus:
    def test_old_record_marked_green(self, renewable_pair):
        old, new = renewable_pair
        assert old.renewal_status == "綠"

    def test_new_record_status_depends_on_window(self, renewable_pair):
        old, new = renewable_pair
        # 新那筆未被續約：若還早 → 灰，30 天內 → 紅
        assert new.renewal_status in ("灰", "紅")

    def test_lonely_record_marked_red(self, lonely_red):
        assert lonely_red.renewal_status == "紅"


class TestListByMonth:
    def test_lists_red_in_correct_month(self, client_as_admin, lonely_red):
        target_month = lonely_red.period_end.month
        target_year = lonely_red.period_end.year
        r = client_as_admin.get(
            f"/api/renewals?month={target_month}&year={target_year}"
        )
        assert r.status_code == 200
        body = r.json()
        ids = [x["id"] for x in body["unrenewed"]]
        assert lonely_red.id in ids

    def test_renewed_appears_in_renewed_bucket(self, client_as_admin, renewable_pair):
        old, _ = renewable_pair
        r = client_as_admin.get(
            f"/api/renewals?month={old.period_end.month}&year={old.period_end.year}"
        )
        assert r.status_code == 200
        body = r.json()
        ids_renewed = [x["id"] for x in body["renewed"]]
        assert old.id in ids_renewed

    def test_category_filter(self, client_as_admin, lonely_red):
        r = client_as_admin.get(
            f"/api/renewals?month={lonely_red.period_end.month}"
            f"&year={lonely_red.period_end.year}"
            f"&category_code=SELF_SERVICE_KTV"
        )
        assert r.status_code == 200
        for item in r.json()["unrenewed"] + r.json()["renewed"] + r.json()["other"]:
            assert item["category_code"] == "SELF_SERVICE_KTV"

    def test_summary_counts_match(self, client_as_admin, lonely_red):
        r = client_as_admin.get(
            f"/api/renewals?month={lonely_red.period_end.month}"
            f"&year={lonely_red.period_end.year}"
        )
        body = r.json()
        s = body["summary"]
        assert s["total"] == s["未續約"] + s["已續約"] + s["其他"]

    def test_invalid_month_400(self, client_as_admin):
        r = client_as_admin.get("/api/renewals?month=13")
        assert r.status_code == 422  # FastAPI Query(ge=1, le=12) → 422
