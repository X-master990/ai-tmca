"""民國年 ↔ 西元年 轉換工具"""
from datetime import date


def roc_to_ad(roc_str: str | None) -> date | None:
    """民國年字串 → 西元 date。

    支援格式:
        '110.11.23' / '110/11/23' / '1101123'

    容錯:
        空字串 / None / 不合法格式 → 回 None
    """
    if not roc_str:
        return None
    if not isinstance(roc_str, str):
        return None

    s = roc_str.replace("/", ".").strip()

    # 7-digit 格式 1101123 → 110.11.23
    if "." not in s and len(s) in (6, 7):
        try:
            roc_y = int(s[:-4])
            m = int(s[-4:-2])
            d = int(s[-2:])
            return date(roc_y + 1911, m, d)
        except (ValueError, TypeError):
            return None

    parts = s.split(".")
    if len(parts) != 3:
        return None
    try:
        roc_y, m, d = (int(x) for x in parts)
        return date(roc_y + 1911, m, d)
    except (ValueError, TypeError):
        return None


def ad_to_roc(d: date | None) -> str | None:
    """西元 date → 民國年字串 '110.11.23'。"""
    if d is None:
        return None
    return f"{d.year - 1911}.{d.month:02d}.{d.day:02d}"


def ad_to_roc_parts(d: date | None) -> tuple[int | None, int | None, int | None]:
    """西元 date → (roc_year, month, day) 三元組，供 Word jinja 模板用。"""
    if d is None:
        return (None, None, None)
    return (d.year - 1911, d.month, d.day)
