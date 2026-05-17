"""12 個申請類型分類定義"""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name_zh: Mapped[str] = mapped_column(String(40), nullable=False)
    sheet_name: Mapped[str | None] = mapped_column(String(40))
    assigned_role: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int | None] = mapped_column(Integer)


# 12 個初始類型（種子資料）
INITIAL_CATEGORIES = [
    ("COMPUTER_KARAOKE",  "電腦伴唱機",         "電腦伴唱機",          "officer_b", 1),
    ("COMMUNITY_BOARD",   "社區管委會",         "社區管委會",          "officer_b", 2),
    ("PUBLIC_KARAOKE",    "公益伴唱機",         "公益伴唱機",          "officer_b", 3),
    ("SELF_SERVICE_KTV",  "自助KTV",            "自助KTV",             "officer_b", 4),
    ("STREET_ARTIST",     "街頭藝人",           "街頭藝人",            "officer_b", 5),
    ("TRANSPORT",         "交通運輸工具",       "交通運輸工具",        "officer_b", 6),
    ("SINGLE_EVENT",      "單場次表演",         "單場次表演",          "officer_a", 7),  # 男生負責
    ("PUBLIC_TRANSMIT",   "公開傳輸",           "公開傳輸",            "officer_b", 8),
    ("FUNERAL",           "告別式",             "告別式",              "officer_b", 9),
    ("AREA_DISPLAY",      "坪數-顯示器",        "坪數-顯示器",         "officer_b", 10),
    ("HALL_ROOM",         "大廳-宴會廳-客房",   "大廳-宴會廳-客房",    "officer_b", 11),
    ("ELECTION",          "競選活動",           "競選活動",            "officer_b", 12),
]
