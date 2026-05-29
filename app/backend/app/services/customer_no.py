"""客戶編號（customer_no）規則與指派。

規則（承辦 2026-05-30 定案）：7 碼 = 1 碼類別前綴 + 6 碼流水。

「同一店家共用一號」的識別鍵 = **店名 + 使用地址**（不可用統編！）：
- 統編不可靠：部分紀錄填的是「音響廠商」統編，多家不相干店家會共用同一統編，
  所以統編完全不納入判斷。
- 改用「正規化店名 + 正規化使用地址」：同店名且同地址 = 同一家。
  - 店名正規化：統一全/半形括號、剝尾端括號別名（「翊麟餐廳(JOJO)」→「翊麟餐廳」）。
  - 地址正規化：全形轉半形、台/臺、去空白、取首段門牌、之↔-、剝樓層/室、去鄰里村冗餘
    （同棟不同樓視為同一家；不同地址＝不同分點，各自獨立號）。
- 地址打法雜亂導致同店被拆者，屬最佳努力之未竟，由承辦於系統內人工併號（寧可分、不可錯併）。
- 流水各前綴各自從 000001 起。
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import Record

PREFIX_BY_CATEGORY: dict[str, str] = {
    "COMPUTER_KARAOKE": "1",  # 電腦伴唱機（營利性）
    "COMMUNITY_BOARD": "1",   # 社區管委會（管委會）
    "SELF_SERVICE_KTV": "2",  # 自助KTV
    "PUBLIC_KARAOKE": "3",    # 公益伴唱機（文化教育/公益）
    "STREET_ARTIST": "4",     # 街頭藝人
    "HALL_ROOM": "5",         # 大廳-宴會廳-客房（旅館飯店）
    "AREA_DISPLAY": "5",      # 坪數-顯示器（營業商號）
    "TRANSPORT": "6",         # 交通運輸工具
    "SINGLE_EVENT": "7",      # 單場次表演
    "FUNERAL": "7",           # 告別式
    "ELECTION": "7",          # 競選活動
    "PUBLIC_TRANSMIT": "9",   # 公開傳輸（公傳）
}

_FW_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")  # 全形數字→半形
# 有效統編 = 剛好 8 碼半形數字（保留作辨識用，但**不參與**客戶編號分組）
_TAX_RE = re.compile(r"[0-9]{8}")
# 店名尾端括號（前面已統一為半形），如「○○餐廳(別名)」
_TAIL_PAREN_RE = re.compile(r"\([^()]*\)\s*$")
# 地址：多門牌/備註分隔符（取第一段）。只用 / ／ 換行 ; —— 不含「、，」因其多為樓層範圍（1、2樓）
_ADDR_SEP_RE = re.compile(r"[\n\r/／;；]")
# 地址：尾端樓層/室，如「…號1樓」「…號1、2樓」「…號4F-1」「…號B1」「…室」
_ADDR_FLOOR_RE = re.compile(
    r"(?:[Bb]?\d+(?:[~～\-、,和至及]\d+)*\s*(?:樓|[Ff])(?:-?\d+)?|地下\d*樓?|[Bb]\d+|\d+室)\s*$"
)
# 地址：只剝安全的「N鄰」（里/村名易與區/鄉名相連，剝除會毀地址，故不處理）
_ADDR_DROP_RE = re.compile(r"\d+鄰")


def prefix_for(category_code: str) -> str | None:
    return PREFIX_BY_CATEGORY.get(category_code)


def _norm(s: str | None) -> str:
    return (s or "").strip()


def valid_tax(tax_id: str | None) -> str | None:
    """正規化後的 8 碼統編（全形轉半形）；非 8 碼數字 → None。
    註：統編僅供辨識/顯示，**不**用於客戶編號分組（承辦：統編不可靠）。"""
    t = _norm(tax_id).translate(_FW_DIGITS)
    return t if _TAX_RE.fullmatch(t) else None


def norm_holder_name(name: str | None) -> str:
    """正規化持證者店名：統一全/半形括號、剝尾端括號別名。

    例：「翊麟餐廳(JOJO)」「翊麟餐廳（JOJO）」→「翊麟餐廳」。
    整串都是括號者（如「(無店名)」）不剝，避免變空字串。
    """
    s = _norm(name).replace("（", "(").replace("）", ")")
    while True:
        stripped = _TAIL_PAREN_RE.sub("", s).strip()
        if stripped == s or not stripped:
            break
        s = stripped
    return s


def norm_address(addr: str | None) -> str:
    """正規化使用地址，吸收常見打法差異，讓同址不同寫法能對齊。

    全形數字→半形、臺→台、取首段門牌（切掉分隔符與括號備註）、之↔-、
    去鄰/里/村冗餘、反覆剝尾端樓層/室。
    """
    s = _norm(addr)
    if not s:
        return ""
    s = s.translate(_FW_DIGITS).replace("臺", "台")
    s = s.replace("（", "(").replace("）", ")").replace("，", ",").replace("－", "-")
    s = re.split(r"[(（]", s)[0]          # 丟掉括號備註，如「(世貿一館)」
    s = _ADDR_SEP_RE.split(s)[0]          # 多門牌取第一段
    s = s.replace("之", "-")              # 「197之11號」≡「197-11號」
    s = re.sub(r"\s+", "", s)
    s = _ADDR_DROP_RE.sub("", s)          # 去「N鄰」「○○里」「○○村」
    prev = None
    while prev != s:                      # 反覆剝尾端樓層（「…號1、2樓」→「…號」）
        prev = s
        s = _ADDR_FLOOR_RE.sub("", s)
    return s


def holder_key(holder_name: str | None, use_address: str | None) -> str | None:
    """店家識別鍵（同前綴內）：正規化店名 + 正規化使用地址。

    - 同店名且同地址 → 同一家（即使統編不同/有音響廠商統編）。
    - 同店名但不同地址 → 各自獨立（不同分點）。
    - 統編完全不納入（承辦：不可靠）。
    回傳 None 表示無店名 → 不配號。
    """
    name = norm_holder_name(holder_name)
    if not name:
        return None
    return f"{name}|{norm_address(use_address)}"


def find_existing_no(
    db: Session, prefix: str, holder_name: str | None, use_address: str | None
) -> str | None:
    """同前綴下，與本筆「店名+地址識別鍵」相同且已配發過的客戶編號 → 沿用。

    正規化在 Python 端做，與回填腳本共用同一套 holder_key，確保 runtime 與 backfill 一致。
    """
    key = holder_key(holder_name, use_address)
    if key is None:
        return None
    rows = (
        db.query(Record.customer_no, Record.holder_name, Record.use_address)
        .filter(Record.customer_no.isnot(None))
        .filter(Record.customer_no.like(f"{prefix}%"))
        .order_by(Record.customer_no)  # 決定性：同一 key 對多號時固定回傳最小號
        .distinct()
        .all()
    )
    for no, hn, addr in rows:
        if holder_key(hn, addr) == key:
            return no
    return None


def _conforms(no: str | None, prefix: str) -> bool:
    """是否為標準 7 碼格式 prefix + 6 位數字。"""
    return bool(no) and len(no) == 7 and no[0] == prefix and no[1:].isdigit()


def next_serial(db: Session, prefix: str) -> int:
    """該前綴目前最大流水 + 1。只認標準 7 碼格式，跳過髒值/手動值，
    避免單一不合規 customer_no 讓 int() 爆掉、卡死整個類別的配號。"""
    rows = (
        db.query(Record.customer_no)
        .filter(Record.customer_no.like(f"{prefix}%"))
        .distinct()
        .all()
    )
    mx = 0
    for (no,) in rows:
        if _conforms(no, prefix):
            mx = max(mx, int(no[1:]))
    return mx + 1


def assign_for_record(db: Session, rec: Record) -> str | None:
    """為單筆 record 指派客戶編號（新增 / 續約時用）。
    已有號、無對應前綴、或無店名 → 不動。回傳指派的號（或 None）。"""
    if rec.customer_no:
        return rec.customer_no
    prefix = prefix_for(rec.category_code)
    if not prefix or not _norm(rec.holder_name):
        return None
    existing = find_existing_no(db, prefix, rec.holder_name, rec.use_address)
    if existing:
        rec.customer_no = existing
        return existing
    serial = next_serial(db, prefix)
    rec.customer_no = f"{prefix}{serial:06d}"
    return rec.customer_no
