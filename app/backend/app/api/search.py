"""Search API — 全域搜尋 + 代辦人交叉查詢"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, or_, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Record, User
from app.schemas.record import RecordOut

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(..., min_length=1, max_length=120, description="搜尋關鍵字"),
    category_code: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """全域搜尋。
    - 先試 full-text (`search_vec @@ plainto_tsquery('simple', :q)`)
    - 再用 LIKE 對 holder_name / applicant_name / cert_no / invoice_no / tax_id 做次掃描
    - 合併去重後回前 N 筆，依 issued_date desc。
    """
    keyword = q.strip()
    # full-text
    fts_sql = text(
        """
        SELECT id FROM records
        WHERE search_vec @@ plainto_tsquery('simple', :q)
        """
    )
    ids_fts = [r.id for r in db.execute(fts_sql, {"q": keyword}).fetchall()]

    # LIKE backfill — 補抓 search_vec 沒涵蓋（例：含特殊字、tokenize 失敗的）
    like = f"%{keyword}%"
    fallback = (
        db.query(Record.id)
        .filter(
            or_(
                Record.holder_name.ilike(like),
                Record.applicant_name.ilike(like),
                Record.cert_no.ilike(like),
                Record.invoice_no.ilike(like),
                Record.tax_id.ilike(like),
                Record.invoice_title.ilike(like),
                Record.officer.ilike(like),
                Record.use_address.ilike(like),
            )
        )
        .limit(limit * 2)
        .all()
    )
    ids_like = [r.id for r in fallback]

    # 合併、保留順序、去重
    seen: set[int] = set()
    merged: list[int] = []
    for i in ids_fts + ids_like:
        if i not in seen:
            seen.add(i)
            merged.append(i)
        if len(merged) >= limit:
            break

    if not merged:
        return {"q": keyword, "total": 0, "by_category": {}, "results": []}

    q_rows = db.query(Record).filter(Record.id.in_(merged))
    if category_code:
        q_rows = q_rows.filter(Record.category_code == category_code)
    rows = q_rows.order_by(desc(Record.issued_date.nulls_last()), desc(Record.id)).all()

    by_category: dict[str, int] = {}
    for r in rows:
        by_category[r.category_code] = by_category.get(r.category_code, 0) + 1

    return {
        "q": keyword,
        "total": len(rows),
        "by_category": by_category,
        "results": [RecordOut.model_validate(r) for r in rows],
    }


@router.get("/agents")
def agents(
    name: str = Query(..., min_length=1, max_length=80),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """代辦人交叉查詢：輸入 applicant_name，列出該人所有 holder + records。"""
    like = f"%{name.strip()}%"
    rows = (
        db.query(Record)
        .filter(Record.applicant_name.ilike(like))
        .order_by(desc(Record.issued_date.nulls_last()), desc(Record.id))
        .limit(500)
        .all()
    )

    # 依 (applicant_name, holder_name) 分組
    holders: dict[tuple[str, str], list[Record]] = {}
    for r in rows:
        key = (r.applicant_name or "", r.holder_name or "")
        holders.setdefault(key, []).append(r)

    groups = []
    for (agent, holder), recs in sorted(holders.items()):
        groups.append({
            "applicant_name": agent,
            "holder_name": holder,
            "count": len(recs),
            "categories": sorted({r.category_code for r in recs}),
            "records": [RecordOut.model_validate(r) for r in recs[:20]],  # 每組最多顯示 20 筆
        })

    distinct_holders = len({h for (_, h) in holders.keys() if h})

    return {
        "query_name": name,
        "total_records": len(rows),
        "distinct_holders": distinct_holders,
        "groups": groups,
    }
