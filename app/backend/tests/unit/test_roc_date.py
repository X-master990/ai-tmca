"""民國年 ↔ 西元年 轉換 unit tests"""
from datetime import date

import pytest

from app.utils.roc_date import ad_to_roc, ad_to_roc_parts, roc_to_ad


class TestRocToAd:
    def test_dot_format(self):
        assert roc_to_ad("110.11.23") == date(2021, 11, 23)

    def test_slash_format(self):
        assert roc_to_ad("114/05/16") == date(2025, 5, 16)

    def test_seven_digit_format(self):
        assert roc_to_ad("1140516") == date(2025, 5, 16)

    def test_six_digit_format(self):
        # 民國 99 年 5 月 16 日
        assert roc_to_ad("990516") == date(2010, 5, 16)

    def test_empty_string_returns_none(self):
        assert roc_to_ad("") is None

    def test_none_returns_none(self):
        assert roc_to_ad(None) is None

    def test_non_string_returns_none(self):
        assert roc_to_ad(12345) is None  # type: ignore[arg-type]

    def test_garbage_returns_none(self):
        assert roc_to_ad("abc") is None
        assert roc_to_ad("xx.yy.zz") is None

    def test_invalid_month_returns_none(self):
        # 13 月不存在 → date() ValueError → None
        assert roc_to_ad("110.13.45") is None

    def test_invalid_day_returns_none(self):
        # 2 月 30 號不存在
        assert roc_to_ad("110.02.30") is None

    def test_with_whitespace(self):
        assert roc_to_ad(" 110.11.23 ") == date(2021, 11, 23)

    def test_single_digit_month_day(self):
        # 點分隔可以接受單位數
        assert roc_to_ad("110.1.1") == date(2021, 1, 1)


class TestAdToRoc:
    def test_basic(self):
        assert ad_to_roc(date(2021, 11, 23)) == "110.11.23"

    def test_pads_month_day(self):
        assert ad_to_roc(date(2025, 1, 5)) == "114.01.05"

    def test_none_returns_none(self):
        assert ad_to_roc(None) is None


class TestRoundtrip:
    @pytest.mark.parametrize("d", [
        date(2021, 11, 23),
        date(2025, 5, 16),
        date(2010, 1, 1),
        date(2099, 12, 31),
    ])
    def test_ad_roc_ad(self, d):
        assert roc_to_ad(ad_to_roc(d)) == d


class TestAdToRocParts:
    def test_basic(self):
        assert ad_to_roc_parts(date(2021, 11, 23)) == (110, 11, 23)

    def test_none(self):
        assert ad_to_roc_parts(None) == (None, None, None)
