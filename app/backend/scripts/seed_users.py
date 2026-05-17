"""種子腳本：建立 5 個預設帳號（4 個角色 + admin）

跑法:
    docker compose exec backend python scripts/seed_users.py
"""
import sys
from pathlib import Path

# 把 backend 根目錄加進 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import User

DEFAULT_PASSWORD = "Tmca0001!"

SEED_USERS = [
    ("officer_a",  "陳大華（單場次）",   "officer_a"),
    ("officer_b",  "王小美（其他）",     "officer_b"),
    ("accountant", "陳會計",             "accountant"),
    ("issuer",     "張核發",             "issuer"),
    ("admin",      "系統管理員",         "admin"),
]


def main():
    db = SessionLocal()
    try:
        for username, display_name, role in SEED_USERS:
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                print(f"  [SKIP] {username} 已存在")
                continue
            u = User(
                username=username,
                password_hash=hash_password(DEFAULT_PASSWORD),
                display_name=display_name,
                role=role,
                is_active=True,
            )
            db.add(u)
            print(f"  [+] {username} ({role}) 已建立")
        db.commit()
        print(f"\n完成。預設密碼: {DEFAULT_PASSWORD}（記得改！）")
    finally:
        db.close()


if __name__ == "__main__":
    main()
