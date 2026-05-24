"""一次性回填客戶編號 customer_no 到既有全表。

規則見 app/services/customer_no.py：7碼 = 1碼類別前綴 + 6碼流水，
同前綴下「持證者名稱+統編」相同 = 同一店家共用一號，流水各前綴各自從 000001。

指派順序：依 record id 由小到大（≈ 原匯入順序），每遇到新店家就給下一個流水。
不覆蓋既有 customer_no。無持證者或無對應前綴的紀錄 → 留空（會列出統計）。

用法：
    python scripts/assign_customer_no.py            # 乾跑（不寫入）
    python scripts/assign_customer_no.py --apply    # 實際寫入
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models import Record
from app.services.customer_no import PREFIX_BY_CATEGORY


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="實際寫入 DB（預設乾跑）")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        rows = db.query(Record).order_by(Record.id).all()

        serial: dict[str, int] = defaultdict(int)        # prefix -> 最後流水
        group_no: dict[tuple, str] = {}                  # (prefix,holder,tax) -> customer_no
        assigned = 0
        skipped_no_prefix = 0
        skipped_no_holder = 0
        kept = 0  # 已有號不動

        for rec in rows:
            if rec.customer_no:
                kept += 1
                continue
            prefix = PREFIX_BY_CATEGORY.get(rec.category_code)
            if not prefix:
                skipped_no_prefix += 1
                continue
            holder = (rec.holder_name or "").strip()
            if not holder:
                skipped_no_holder += 1
                continue
            key = (prefix, holder, (rec.tax_id or "").strip())
            no = group_no.get(key)
            if no is None:
                serial[prefix] += 1
                no = f"{prefix}{serial[prefix]:06d}"
                group_no[key] = no
            if args.apply:
                rec.customer_no = no
            assigned += 1

        if args.apply:
            db.commit()
    finally:
        db.close()

    print(f"\n{'=' * 56}")
    print(f"客戶編號回填{'（已寫入）' if args.apply else '（乾跑，未寫入）'}")
    print(f"  指派欄位數（紀錄）: {assigned}")
    print(f"  不重複店家數      : {len(group_no)}")
    print(f"  已有號保留        : {kept}")
    print(f"  無持證者跳過      : {skipped_no_holder}")
    print(f"  無對應前綴跳過    : {skipped_no_prefix}")
    print("  各前綴店家數 / 末流水:")
    for p in sorted(serial):
        print(f"    {p}: {serial[p]} 店  (末號 {p}{serial[p]:06d})")
    print(f"{'=' * 56}\n")


if __name__ == "__main__":
    main()
