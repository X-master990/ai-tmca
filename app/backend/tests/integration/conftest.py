"""Integration test infrastructure

策略：
- session-scope：建立獨立的 `tmca_test` DB、跑 alembic 到最新版、seed users + categories
- function-scope：每個測試包在外層 transaction + nested savepoint，測完 rollback、互不污染
- TestClient 不用 `with`，避開 lifespan（APScheduler 啟動）
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import get_db
from app.main import app
from app.models import Category, User

# 從 DATABASE_URL 取連線字串，把 DB name 換成 tmca_test
_BASE_URL = os.environ.get("DATABASE_URL") or os.environ.get(
    "ADMIN_DB_URL",
    "postgresql+psycopg://tmca:changeme_in_production@db:5432/tmca",
)
ADMIN_URL = _BASE_URL  # 用同一組 credential，連 default db 來建/刪 tmca_test
TEST_DB_NAME = "tmca_test"
TEST_URL = ADMIN_URL.rsplit("/", 1)[0] + f"/{TEST_DB_NAME}"

BACKEND_ROOT = Path(__file__).resolve().parents[2]

ROLES = ["officer_a", "officer_b", "accountant", "issuer", "admin"]
DEFAULT_PASSWORD = "Tmca0001!"


def _drop_db(admin_url: str, db_name: str) -> None:
    eng = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with eng.connect() as conn:
        conn.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
        ))
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    eng.dispose()


@pytest.fixture(scope="session")
def _test_db_url():
    """建立 tmca_test、跑 alembic 到 head、回 URL。Session 結束時 drop DB。"""
    _drop_db(ADMIN_URL, TEST_DB_NAME)
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()

    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_URL
    res = subprocess.run(
        ["alembic", "upgrade", "head"],
        env=env, capture_output=True, text=True, cwd=str(BACKEND_ROOT),
    )
    if res.returncode != 0:
        raise RuntimeError(f"alembic upgrade failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

    yield TEST_URL

    _drop_db(ADMIN_URL, TEST_DB_NAME)


@pytest.fixture(scope="session")
def test_engine(_test_db_url):
    eng = create_engine(_test_db_url, pool_pre_ping=True, future=True)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session", autouse=True)
def _seed(test_engine):
    """seed users + categories — 共用、不會被各測試 rollback 動到（因為在 session 範圍 commit）。"""
    from app.models.category import INITIAL_CATEGORIES

    with Session(test_engine, expire_on_commit=False) as s:
        existing_cats = {c.code for c in s.query(Category).all()}
        for code, name_zh, sheet, assigned, sort_order in INITIAL_CATEGORIES:
            if code not in existing_cats:
                s.add(Category(
                    code=code, name_zh=name_zh, sheet_name=sheet,
                    assigned_role=assigned, sort_order=sort_order,
                ))
        s.commit()

        pwd = hash_password(DEFAULT_PASSWORD)
        for role in ROLES:
            if not s.query(User).filter_by(username=role).first():
                s.add(User(
                    username=role,
                    password_hash=pwd,
                    display_name=role,
                    role=role,
                    is_active=True,
                ))
        s.commit()


@pytest.fixture()
def db(test_engine):
    """Per-test session。外層 transaction + savepoint：app 內 `session.commit()` 只 commit savepoint。"""
    connection = test_engine.connect()
    trans = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    yield session
    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    """FastAPI TestClient — 不用 `with`，避免 lifespan 啟動 scheduler。"""
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def _login(client: TestClient, username: str) -> TestClient:
    r = client.post("/api/auth/login", json={"username": username, "password": DEFAULT_PASSWORD})
    assert r.status_code == 200, f"login as {username} failed: {r.status_code} {r.text}"
    return client


@pytest.fixture()
def client_as_officer_a(client):
    return _login(client, "officer_a")


@pytest.fixture()
def client_as_officer_b(client):
    return _login(client, "officer_b")


@pytest.fixture()
def client_as_accountant(client):
    return _login(client, "accountant")


@pytest.fixture()
def client_as_issuer(client):
    return _login(client, "issuer")


@pytest.fixture()
def client_as_admin(client):
    return _login(client, "admin")


# ───────────────────────── 資料建構 helpers ─────────────────────────

@pytest.fixture()
def make_record(db):
    """Factory：建一筆 record，回 (id, dict)。可指定 category_code 與任意欄位。"""
    from app.models import Record

    def _factory(**kwargs) -> Record:
        defaults = {
            "category_code": "SINGLE_EVENT",
            "issuance_status": "紅",
        }
        defaults.update(kwargs)
        rec = Record(**defaults)
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec

    return _factory
