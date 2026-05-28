# TMCA 單一容器部署用 Dockerfile（Railway 等平台）
# build context = repo 根目錄，需同時拿到 app/frontend、app/backend、templates、總表 xlsx。
# 本機開發仍用 app/docker-compose.yml（前後端分開），此檔不影響開發流程。

# ── 階段 1：build 前端（React + Vite）──────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY app/frontend/package.json app/frontend/package-lock.json* ./
RUN npm install
COPY app/frontend/ ./
RUN npm run build          # 產出 /fe/dist

# ── 階段 2：後端（FastAPI）+ 靜態前端 + 模板 + 種子檔 ──────────
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY app/backend/requirements.txt ./
RUN pip install -r requirements.txt

# 後端程式（含 alembic、scripts、entrypoint）
COPY app/backend/ ./

# 證書/發票模板（後端產檔時讀 /var/tmca/templates）
COPY templates/ /var/tmca/templates/
RUN mkdir -p /var/tmca/output

# 一次性種子用的總表 xlsx
COPY ["110-115年 總表.xlsx", "/app/seed/總表.xlsx"]

# 前端 build 成果 → 由 FastAPI 提供（main.py 偵測 /app/static）
COPY --from=frontend /fe/dist /app/static

RUN chmod +x entrypoint.sh

EXPOSE 8000
CMD ["./entrypoint.sh"]
