"""SQLAlchemy engine、session、Base"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
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
