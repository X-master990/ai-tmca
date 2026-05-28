"""TMCA 音樂版權授權系統 — FastAPI entry"""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.exports import router as exports_router
from app.api.invoices import router as invoices_router
from app.api.records import router as records_router
from app.api.renewals import router as renewals_router
from app.api.reports import router as reports_router
from app.api.search import router as search_router
from app.config import settings
from app.database import engine
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"[TMCA] Starting up. DB: {settings.database_url.split('@')[-1]}")
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    print("[TMCA] Shutting down.")


app = FastAPI(
    title="TMCA 音樂版權授權系統",
    description="社團法人台灣音樂著作權集體管理協會 — 內部作業 API",
    version="0.1.0-phase-0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS（給開發階段直連用；Caddy 反向代理時其實同源不需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(exports_router)
app.include_router(invoices_router)
app.include_router(records_router)
app.include_router(renewals_router)
app.include_router(reports_router)
app.include_router(search_router)


@app.get("/api/health")
def health():
    """檢查 DB 通不通，回 server 狀態。"""
    db_ok = False
    db_msg = ""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_msg = str(e)

    return {
        "status": "ok" if db_ok else "degraded",
        "service": "tmca-backend",
        "version": "0.1.0-phase-0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "db": {"ok": db_ok, "message": db_msg or "connected"},
    }


@app.get("/api/")
def root():
    """簡介。"""
    return {
        "name": "TMCA 音樂版權授權系統 API",
        "version": "0.1.0-phase-0",
        "docs": "/api/docs",
        "health": "/api/health",
    }


# ────────────────────────────────────────────────────────────────
# 靜態前端（單一容器部署時，後端同時提供 React build）
# 本機 docker-compose 開發無此目錄 → 不註冊，由 nginx/Caddy 負責前端。
# 必須放在所有 /api router 之後：catch-all 為最後註冊，/api/* 會先被匹配。
# ────────────────────────────────────────────────────────────────
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

if os.path.isdir(STATIC_DIR):
    _index = os.path.join(STATIC_DIR, "index.html")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        """檔案存在就回該檔，否則回 index.html（支援 React Router 前端路由）。"""
        candidate = os.path.normpath(os.path.join(STATIC_DIR, full_path))
        # 防目錄穿越：只允許 STATIC_DIR 底下的檔案
        if candidate.startswith(STATIC_DIR + os.sep) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(_index)
