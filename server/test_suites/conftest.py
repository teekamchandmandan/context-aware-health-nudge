import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVER_DIR = Path(__file__).resolve().parents[1]

if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

os.environ.setdefault("DATABASE_PATH", str(SERVER_DIR / "test_api.db"))
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("OPENAI_API_KEY", "")

from app.database import _connect
from app.main import app
from app.seed import reset_and_seed


@pytest.fixture
def api_client():
    reset_and_seed()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def db_conn():
    reset_and_seed()
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()