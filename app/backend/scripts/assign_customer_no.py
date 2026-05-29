"""回填 / 重配客戶編號 customer_no 到既有全表。

規則見 app/services/customer_no.py（與此腳本共用 holder_key）：
  7碼 = 1碼類別前綴 + 6碼流水；店家識別鍵 = 正規化店名 + 正規化使用地址（不用統編）。
  同前綴下同店名+同地址共用一號，流水各前綴各自從 000001。

指派順序：依 record id 由小到大（≈ 原匯入順序），每遇到新店家就給下一個流水。

模式：
  python scripts/assign_customer_no.py             # 乾跑：只補空號（不覆蓋既有）
  python scripts/assign_customer_no.py --apply     # 寫入：只補空號
  python scripts/assign_customer_no.py --reassign  # 乾跑：清空全部重配（新規則對既有資料生效）
  python scripts/assign_customer_no.py --reassign --apply   # 寫入：清空全部重配

無店名或無對應前綴的紀錄 → 留空（會列出統計）。
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models import Record
from app.services.customer_no import PREFIX_BY_CATEGORY, holder_key


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="實際寫入 DB（預設乾跑）")
    ap.add_argument(
        "--reassign",
        action="store_true",
        help="清空所有 customer_no 後整批重配（讓新識別規則對既有資料生效）",
    )
    args = ap.parse_args()

    db = SessionLocal()
    try:
        rows = db.query(Record).order_by(Record.id).all()

        serial: dict[str, int] = defaultdict(int)        # prefix -> 最後流水
        group_no: dict[tuple[str, str], str] = {}        # (prefix, holder_key) -> customer_no
        # 每個 group 蒐集原始店名/地址，供「同店不同寫法被併」的呈現
        group_names: dict[tuple[str, str], set[str]] = defaultdict(set)
        group_addrs: dict[tuple[str, str], set[str]] = defaultdict(set)
        # 同前綴 + 同正規化店名 出現過幾種地址 → 偵測「同名被地址拆成多號」
        name_to_nos: dict[tuple[str, str], set[str]] = defaultdict(set)

        assigned = 0
        skipped_no_prefix = 0
        skipped_no_holder = 0
        kept = 0          # 已有號不動（僅補空號模式）
        changed = 0       # 重配後號碼與原本不同

        for rec in rows:
            old_no = rec.customer_no
            if old_no and not args.reassign:
                kept += 1
                continue
            prefix = PREFIX_BY_CATEGORY.get(rec.category_code)
            if not prefix:
                skipped_no_prefix += 1
                if args.reassign and args.apply and old_no:
                    rec.customer_no = None  # 重配：失去資格者清空，符合「清空全部重配」
                    changed += 1
                continue
            hk = holder_key(rec.holder_name, rec.use_address)
            if hk is None:
                skipped_no_holder += 1
                if args.reassign and args.apply and old_no:
                    rec.customer_no = None
                    changed += 1
                continue
            key = (prefix, hk)
            no = group_no.get(key)
            if no is None:
                serial[prefix] += 1
                no = f"{prefix}{serial[prefix]:06d}"
                group_no[key] = no
            group_names[key].add((rec.holder_name or "").strip())
            group_addrs[key].add((rec.use_address or "").strip())
            name_to_nos[(prefix, hk.split("|", 1)[0])].add(no)
            if old_no and old_no != no:
                changed += 1
            if args.apply:
                rec.customer_no = no
            assigned += 1

        if args.apply:
            db.commit()
    finally:
        db.close()

    mode = "清空重配" if args.reassign else "補空號"
    state = "已寫入" if args.apply else "乾跑，未寫入"
    print(f"\n{'=' * 60}")
    print(f"客戶編號{mode}（{state}）　識別鍵 = 正規化店名 + 正規化地址")
    print(f"  指派欄位數（紀錄）  : {assigned}")
    print(f"  不重複店家數        : {len(group_no)}")
    if args.reassign:
        print(f"  號碼與原本不同      : {changed}")
    else:
        print(f"  已有號保留          : {kept}")
    print(f"  無店名跳過          : {skipped_no_holder}")
    print(f"  無對應前綴跳過      : {skipped_no_prefix}")
    if not args.reassign:
        print("  ※ 補空號模式：以下統計只涵蓋本次新填的列，不代表全表（全表請用 --reassign 乾跑）")
    print("  各前綴店家數 / 末流水:")
    for p in sorted(serial):
        print(f"    {p}: {serial[p]} 家  (末號 {p}{serial[p]:06d})")

    # 併號群：同一號底下出現 ≥2 種原始店名或地址寫法（= 同店不同寫法被收成一號）
    merges = [
        (k, group_names[k], group_addrs[k])
        for k in group_no
        if len(group_names[k]) > 1 or len(group_addrs[k]) > 1
    ]
    # 同店名被地址拆成多號（可能是真不同分點，也可能是地址打法不同造成的 under-merge）
    name_split = [(k, nos) for k, nos in name_to_nos.items() if len(nos) > 1]
    print(f"\n  併號群（同店不同寫法收成一號）  : {len(merges)} 家")
    print(f"  同店名被地址拆成多號（請複查）  : {len(name_split)} 個店名")
    print("  ※ 地址打法雜亂時同店可能被拆，屬最佳努力；請承辦於系統內人工併號（寧分勿錯併）")

    if merges:
        print("\n  —— 併號樣本（同一號收進多種店名/地址寫法，前 30）——")
        for (prefix, hk), names, addrs in sorted(merges, key=lambda kv: -(len(kv[1]) + len(kv[2])))[:30]:
            label = " ｜ ".join(sorted(n for n in names if n))
            print(f"    {group_no[(prefix, hk)]}  ←  {label}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
