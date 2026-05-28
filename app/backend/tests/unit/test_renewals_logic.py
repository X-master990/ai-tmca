"""續約狀態分類規則 unit tests（純函數版本）

對應 app/services/renewals.py 的 SQL 規則，但用純 Python 重寫便於單元測試。
"""
from datetime import date, timedelta

import pytest

from app.services.renewals import RenewalCandidate, classify_renewal_status


def make(
    id: int = 1,
    category_code: str = "RESTAURANT",
    holder_name: str | None = "玉亭餐廳",
    tax_id: str | None = "12345678",
    period_end: date | None = None,
) -> RenewalCandidate:
    return RenewalCandidate(
        id=id,
        category_code=category_code,
        holder_name=holder_name,
        tax_id=tax_id,
        period_end=period_end,
    )


TODAY = date(2026, 5, 18)


class TestGreyOnMissingData:
    def test_no_holder_name(self):
        rec = make(holder_name=None, period_end=TODAY + timedelta(days=10))
        assert classify_renewal_status(rec, [], today=TODAY) == "灰"

    def test_no_period_end(self):
        rec = make(period_end=None)
        assert classify_renewal_status(rec, [], today=TODAY) == "灰"

    def test_both_missing(self):
        rec = make(holder_name=None, period_end=None)
        assert classify_renewal_status(rec, [], today=TODAY) == "灰"


class TestGreenWhenRenewed:
    def test_same_holder_later_period_end_is_green(self):
        rec = make(id=1, period_end=date(2026, 5, 31))
        renew = make(id=2, period_end=date(2027, 5, 31))
        assert classify_renewal_status(rec, [renew], today=TODAY) == "綠"

    def test_self_does_not_count(self):
        # 不能用自己當作續約對象，即使 period_end 相同
        rec = make(id=1, period_end=date(2026, 5, 31))
        assert classify_renewal_status(rec, [rec], today=TODAY) == "紅"

    def test_different_category_does_not_count(self):
        rec = make(id=1, category_code="RESTAURANT", period_end=date(2026, 5, 31))
        other = make(id=2, category_code="HOTEL", period_end=date(2027, 5, 31))
        # 不同類型 → 不算續約 → 30 天內到期 → 紅
        assert classify_renewal_status(rec, [other], today=TODAY) == "紅"

    def test_different_holder_does_not_count(self):
        rec = make(id=1, holder_name="玉亭", period_end=date(2026, 5, 31))
        other = make(id=2, holder_name="阿信", period_end=date(2027, 5, 31))
        assert classify_renewal_status(rec, [other], today=TODAY) == "紅"

    def test_different_tax_id_does_not_count(self):
        rec = make(id=1, tax_id="11111111", period_end=date(2026, 5, 31))
        other = make(id=2, tax_id="22222222", period_end=date(2027, 5, 31))
        assert classify_renewal_status(rec, [other], today=TODAY) == "紅"

    def test_rec_tax_id_null_is_match(self):
        # 規則：兩邊任一為 NULL 視為相符
        rec = make(id=1, tax_id=None, period_end=date(2026, 5, 31))
        other = make(id=2, tax_id="12345678", period_end=date(2027, 5, 31))
        assert classify_renewal_status(rec, [other], today=TODAY) == "綠"

    def test_other_tax_id_null_is_match(self):
        rec = make(id=1, tax_id="12345678", period_end=date(2026, 5, 31))
        other = make(id=2, tax_id=None, period_end=date(2027, 5, 31))
        assert classify_renewal_status(rec, [other], today=TODAY) == "綠"

    def test_other_period_end_earlier_not_renewal(self):
        # other 比 rec 早到期 → 不算續約
        rec = make(id=1, period_end=date(2026, 5, 31))
        earlier = make(id=2, period_end=date(2025, 5, 31))
        assert classify_renewal_status(rec, [earlier], today=TODAY) == "紅"

    def test_other_period_end_equal_not_renewal(self):
        # 相等也不算續約（SQL 用 > 不是 >=）
        rec = make(id=1, period_end=date(2026, 5, 31))
        equal = make(id=2, period_end=date(2026, 5, 31))
        assert classify_renewal_status(rec, [equal], today=TODAY) == "紅"


class TestRedWindow:
    def test_today_is_red(self):
        rec = make(period_end=TODAY)
        assert classify_renewal_status(rec, [], today=TODAY) == "紅"

    def test_30_days_out_is_red_inclusive(self):
        rec = make(period_end=TODAY + timedelta(days=30))
        assert classify_renewal_status(rec, [], today=TODAY) == "紅"

    def test_31_days_out_is_grey(self):
        rec = make(period_end=TODAY + timedelta(days=31))
        assert classify_renewal_status(rec, [], today=TODAY) == "灰"

    def test_far_future_is_grey(self):
        rec = make(period_end=TODAY + timedelta(days=365))
        assert classify_renewal_status(rec, [], today=TODAY) == "灰"

    def test_already_expired_is_grey_not_red(self):
        # 已過期 backlog 不該爆紅 — 對應 Phase 4 refine commit
        rec = make(period_end=TODAY - timedelta(days=1))
        assert classify_renewal_status(rec, [], today=TODAY) == "灰"

    def test_long_expired_is_grey(self):
        rec = make(period_end=TODAY - timedelta(days=365))
        assert classify_renewal_status(rec, [], today=TODAY) == "灰"


class TestMixedScenarios:
    def test_renewed_old_records_stay_green_even_if_long_expired(self):
        rec = make(id=1, period_end=date(2020, 1, 1))
        renew = make(id=2, period_end=date(2027, 5, 31))
        assert classify_renewal_status(rec, [renew], today=TODAY) == "綠"

    def test_multiple_others_only_one_qualifies(self):
        rec = make(id=1, period_end=date(2026, 5, 31))
        others = [
            make(id=2, holder_name="別人", period_end=date(2030, 1, 1)),  # 不同持證者
            make(id=3, category_code="HOTEL", period_end=date(2030, 1, 1)),  # 不同類型
            make(id=4, period_end=date(2027, 5, 31)),  # ← 真正的續約
        ]
        assert classify_renewal_status(rec, others, today=TODAY) == "綠"


@pytest.mark.parametrize("offset,expected", [
    (-365, "灰"),
    (-1, "灰"),
    (0, "紅"),
    (1, "紅"),
    (15, "紅"),
    (30, "紅"),
    (31, "灰"),
    (60, "灰"),
])
def test_red_window_boundaries(offset, expected):
    rec = make(period_end=TODAY + timedelta(days=offset))
    assert classify_renewal_status(rec, [], today=TODAY) == expected
