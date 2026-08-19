"""
Shared pytest fixtures for the API test suite.

CI wires these env vars to a throwaway MariaDB service container with the
real schema/triggers/procedures/seed data loaded (see
.github/workflows/ci.yml). Locally, point them at your dev MySQL instance
(the same one docker-compose.yml already assumes is running on the host) or
just run `pytest` with no env vars to fall back to config.py's defaults.
"""
import os

# Must be set before `app.core.config.settings` / `app.core.database.engine`
# are imported anywhere, since the engine URL is built once at import time.
os.environ.setdefault("APP_MODE", "public")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "root")
os.environ.setdefault("DB_NAME", "rentease")
os.environ.setdefault("JWT_SECRET", "ci-test-secret")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_placeholder")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "minioadmin")
os.environ.setdefault("S3_SECRET_KEY", "minioadmin")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    # Function-scoped (not session-scoped) deliberately: cookies set by one
    # test (e.g. a successful login in test_auth_integration.py) must not
    # leak into another test's client and make an unauthenticated check
    # pass for the wrong reason.
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_available():
    """
    Skips a test at runtime if no database is reachable, so the smoke tests
    (test_health.py) still pass in environments with no DB at all, while
    the integration tests (test_auth.py) that need seed data can opt in.
    """
    from sqlalchemy import text
    from app.core.database import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("No database reachable — skipping DB-backed test")
    return True
