"""續約函生成 — 讀 jinja 模板(docxtpl) → 填續約資料 → 回 .docx bytes。

模板：/var/tmca/templates/承辦/續約函模板.docx
      （由 scripts/build_renewal_letter_template.py 從原始範例檔產生）

模板變數（皆字串/數字，前端可逐欄覆寫，所見即所印）：
    recipient        受文者（店名/持證者）
    issue_date       發文日期    例 '115年5月29日'
    pay_deadline     繳費期限    例 '115年6月30日'
    period_start     授權起      例 '115 年 06 月 01 日'
    period_end       授權迄      例 '116 年 05 月 31 日'
    business_address 營業地址
    qty              申報台數
    amount           應付金額（含稅）

電腦伴唱機標準費率：每台每年 3,675 元（含稅）。
"""
from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

from docxtpl import DocxTemplate

from app.config import settings
from app.models import Record

TEMPLATE_PATH = Path(settings.template_dir) / "承辦" / "續約函模板.docx"

UNIT_FEE = 3675  # 電腦伴唱機 每台每年含稅標準費（對齊模板條文）

# 模板宣告的全部變數 — 渲染時逐一補空字串，避免 jinja UndefinedError
LETTER_VARS = (
    "recipient",
    "issue_date",
    "pay_deadline",
    "period_start",
    "period_end",
    "business_address",
    "qty",
    "amount",
)


def roc_long(d: date) -> str:
    """西元 date → '115 年 06 月 01 日'（民國、月日補零、空格分隔；對齊授權時間欄）。"""
    return f"{d.year - 1911} 年 {d.month:02d} 月 {d.day:02d} 日"


def roc_short(d: date) -> str:
    """西元 date → '115年5月29日'（民國、月日不補零；對齊發文日期/繳費期限欄）。"""
    return f"{d.year - 1911}年{d.month}月{d.day}日"


def _plus_one_year_minus_day(start: date) -> date:
    """迄日 = 起日 + 1 年 - 1 天（與 api/renewals._plus_one_year_minus_day 同義）。"""
    try:
        one_year = start.replace(year=start.year + 1)
    except ValueError:  # 2/29 → 隔年無此日，退到 2/28
        one_year = start.replace(year=start.year + 1, day=28)
    return one_year - timedelta(days=1)


def _minus_one_year_plus_day(end: date) -> date:
    """起日 = 迄日 - 1 年 + 1 天（_plus_one_year_minus_day 的逆運算）。"""
    try:
        prev = end.replace(year=end.year - 1)
    except ValueError:  # 2/29 → 前一年無此日，退到 2/28
        prev = end.replace(year=end.year - 1, day=28)
    return prev + timedelta(days=1)


def _last_day_of_next_month(d: date) -> date:
    """d 的次月最後一天（繳費期限預設；對齊範例：發文 5/12 → 繳費 6/30）。"""
    first_next = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
    first_after = (
        date(first_next.year + 1, 1, 1)
        if first_next.month == 12
        else date(first_next.year, first_next.month + 1, 1)
    )
    return first_after - timedelta(days=1)


def build_prefill(rec: Record, today: date | None = None) -> dict:
    """依 record 計算續約函表單預設值（皆可被前端覆寫）。

    授權期間：
      - rec 本身是續約行（action_type=續約 且有起迄）→ 直接用其期間。
      - 否則（即將到期行）→ 自 period_end 次日起算一年。
      - 只有起日沒迄日 → 自起日起算一年。
    申報台數 = qty（無則 1）；應付金額 = 台數 × 3,675（標準費）。
    發文日期 = 今天；繳費期限 = 次月月底。
    """
    today = today or date.today()
    qty = rec.qty if (rec.qty and rec.qty > 0) else 1

    if rec.action_type == "續約" and (rec.period_start or rec.period_end):
        # 續約行：信任本身登錄的授權期間，缺一邊就以另一邊推算一年，
        # 不可把它的 period_end 當成「舊到期日」往後再滾一年。
        if rec.period_start and rec.period_end:
            ps, pe = rec.period_start, rec.period_end
        elif rec.period_start:
            ps = rec.period_start
            pe = _plus_one_year_minus_day(ps)
        else:  # 只有迄日 → 回推起日
            pe = rec.period_end
            ps = _minus_one_year_plus_day(pe)
    elif rec.period_end:
        # 即將到期行：自舊到期日次日起算一年
        ps = rec.period_end + timedelta(days=1)
        pe = _plus_one_year_minus_day(ps)
    elif rec.period_start:
        ps = rec.period_start
        pe = _plus_one_year_minus_day(ps)
    else:
        ps = pe = None

    return {
        "record_id": rec.id,
        "recipient": rec.holder_name or rec.invoice_title or "",
        "issue_date": roc_short(today),
        "pay_deadline": roc_short(_last_day_of_next_month(today)),
        "period_start": roc_long(ps) if ps else "",
        "period_end": roc_long(pe) if pe else "",
        "business_address": rec.use_address or "",
        "qty": qty,
        "amount": qty * UNIT_FEE,
    }


def render_letter(ctx: dict) -> bytes:
    """以 ctx 填模板，回 .docx bytes。缺項補空字串。

    autoescape=True：店名/地址若含 & < > 等 XML 特殊字元，jinja 會自動跳脫，
    否則會產生非法 XML、讓整份 Word 從該處截斷（例：店名「A&B」「KTV<旗艦店>」）。
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"續約函模板不存在：{TEMPLATE_PATH}")
    tpl = DocxTemplate(str(TEMPLATE_PATH))
    render_ctx = {k: ("" if ctx.get(k) is None else ctx.get(k)) for k in LETTER_VARS}
    tpl.render(render_ctx, autoescape=True)
    buf = BytesIO()
    tpl.save(buf)
    return buf.getvalue()
