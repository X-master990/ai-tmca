"""Pytest setup — make `app` package importable from tests."""
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://tmca:test@localhost:5432/tmca_test")
