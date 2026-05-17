"""TMCA 音樂版權授權系統 — FastAPI entry"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
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
