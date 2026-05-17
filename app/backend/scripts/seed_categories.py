"""種子腳本：建立 12 個 categories

跑法:
    docker compose exec backend python scripts/seed_categories.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models import Category
from app.models.category import INITIAL_CATEGORIES


def main():
    db = SessionLocal()
    try:
        for code, name_zh, sheet_name, role, sort_order in INITIAL_CATEGORIES:
            existing = db.query(Category).filter(Category.code == code).first()
            if existing:
                print(f"  [SKIP] {code} 已存在")
                continue
            c = Category(
                code=code,
                name_zh=name_zh,
                sheet_name=sheet_name,
                assigned_role=role,
                sort_order=sort_order,
            )
            db.add(c)
            print(f"  [+] {code} ({name_zh}) 已建立")
        db.commit()
        print("\n完成。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
