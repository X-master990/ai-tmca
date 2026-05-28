"""SQLAlchemy engine、session、Base"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _normalize_db_url(url: str) -> str:
    """把雲端託管平台（Railway 等）給的 postgres URL 轉成本專案用的 psycopg3 驅動。

    Railway / 多數平台給的是 `postgresql://...`（SQLAlchemy 預設找 psycopg2，未安裝會炸），
    本專案只裝 psycopg3，故統一改寫成 `postgresql+psycopg://`。
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


engine = create_engine(_normalize_db_url(settings.database_url), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base"""
    pass


def get_db():
    """FastAPI dependency: yield 一個 session、用完關掉。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
