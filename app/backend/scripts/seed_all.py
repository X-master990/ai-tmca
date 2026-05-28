"""一鍵冪等種子 — 給容器啟動時自動呼叫（entrypoint.sh）。

行為:
  - 一律跑 seed_categories、seed_users（兩者本來就會跳過既有，重複執行安全）。
  - 僅當 records 表為「0 筆」時，才依序匯入總表 → 回填 → 指派客戶編號。
    已有資料就完全不動，避免重複匯入或覆蓋線上修改。

xlsx 來源: 環境變數 SEED_XLSX，預設 /app/seed/總表.xlsx（由 Dockerfile 打包進映像）。

用法:
    python scripts/seed_all.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = BACKEND_ROOT / "scripts"
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import Record  # noqa: E402

XLSX = Path(os.environ.get("SEED_XLSX", "/app/seed/總表.xlsx"))


def _run(*args: str) -> None:
    print(f"\n$ python {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, *args], cwd=str(BACKEND_ROOT), check=True)


def main() -> None:
    # 基礎種子（冪等：腳本自帶跳過既有）
    _run("scripts/seed_categories.py")
    _run("scripts/seed_users.py")

    # 只有空表才匯入總表
    db = SessionLocal()
    try:
        record_count = db.query(Record).count()
    finally:
        db.close()

    if record_count > 0:
        print(f"\n[seed_all] records 已有 {record_count} 筆 → 跳過匯入。", flush=True)
        return

    if not XLSX.exists():
        print(f"\n[seed_all] ⚠️ 找不到種子檔 {XLSX}，跳過匯入（資料表保持空）。", flush=True)
        return

    print(f"\n[seed_all] records 為空 → 開始匯入 {XLSX}", flush=True)
    _run("scripts/import_excel.py", str(XLSX), "--commit")
    _run("scripts/backfill_cleaned.py", str(XLSX), "--apply", "-o", "/tmp/IMPORT-MANUAL-FIXLIST.md")
    _run("scripts/assign_customer_no.py", "--apply")
    print("\n[seed_all] 完成。", flush=True)


if __name__ == "__main__":
    main()
