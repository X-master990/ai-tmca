"""續約偵測 — 對所有 records 重新計算 renewal_status

規則（依 ADR-002 §四 Phase 4）：
1. 對每筆 R（有 holder_name + period_end）：
   - 若存在另一筆 B 滿足：B.category_code = R.category_code、
     B.holder_name = R.holder_name、
     B.tax_id 相符（或兩邊有任一為 NULL）、
     B.period_end > R.period_end、
     B.id ≠ R.id
     → 表示 R 已被 B 續約 → '綠'
   - 否則：
     - period_end < today + 30d → '紅'（含已過期）
     - 其餘 → '灰'
2. 無 holder_name 或 period_end → '灰'

性能：一條 UPDATE…CASE…EXISTS… 對 14k 筆約 < 1 秒。
"""
from __future__ import annotations

import time
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

# 一條 SQL 處理掉全部 ─ 用 EXISTS 子查詢比對「同一持證者更晚到期的紀錄」
COMPUTE_SQL = text(
    """
    UPDATE records AS r SET renewal_status = CASE
        WHEN r.holder_name IS NULL OR r.period_end IS NULL THEN '灰'
        WHEN EXISTS (
            SELECT 1 FROM records AS r2
            WHERE r2.category_code = r.category_code
              AND r2.holder_name = r.holder_name
              AND (
                  r2.tax_id = r.tax_id
                  OR r2.tax_id IS NULL
                  OR r.tax_id IS NULL
              )
              AND r2.period_end > r.period_end
              AND r2.id <> r.id
        ) THEN '綠'
        WHEN r.period_end <= CURRENT_DATE + INTERVAL '30 days' THEN '紅'
        ELSE '灰'
    END
    """
)

STATS_SQL = text(
    """
    SELECT
        COALESCE(renewal_status, 'null') AS status,
        COUNT(*) AS n
    FROM records
    GROUP BY renewal_status
    ORDER BY n DESC
    """
)


def compute_renewal_status(db: Session) -> dict:
    """跑 UPDATE，回傳統計與耗時。呼叫端負責 commit。"""
    t0 = time.monotonic()
    result = db.execute(COMPUTE_SQL)
    db.commit()
    rows_updated = result.rowcount
    elapsed = time.monotonic() - t0

    stats_rows = db.execute(STATS_SQL).fetchall()
    breakdown = {r.status: r.n for r in stats_rows}

    return {
        "rows_updated": rows_updated,
        "elapsed_seconds": round(elapsed, 3),
        "breakdown": breakdown,
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }
