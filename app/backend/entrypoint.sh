#!/bin/sh
# 容器啟動流程（單一容器部署用）：
#   1. 套用資料庫遷移（建/更新資料表，冪等）
#   2. 種子（首次才匯入總表，seed_all 自帶防呆）
#   3. 啟動 API + 靜態前端
set -e

echo "[entrypoint] alembic upgrade head ..."
alembic upgrade head

echo "[entrypoint] seed_all ..."
python scripts/seed_all.py

echo "[entrypoint] starting uvicorn on port ${PORT:-8000} ..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2
