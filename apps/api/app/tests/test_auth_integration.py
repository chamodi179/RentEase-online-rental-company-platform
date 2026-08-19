"""
Integration tests that require a live database with the schema + seed data
loaded (docs/01_schema.sql, 02_triggers.sql, 03_procedures.sql,
05_seed_data.sql — CI loads all four into the MariaDB service container
before this file runs, see .github/workflows/ci.yml).

Each test depends on the `db_available` fixture, which skips (rather than
fails) when no DB is reachable, so this file is still safe to run locally
without a database.
"""


def test_login_with_seeded_customer_succeeds(client, db_available):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice.perera@example.com", "password": "Customer@123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "alice.perera@example.com"
    assert body["role"] == "customer"
    assert "public_access_token" in resp.cookies


def test_login_with_wrong_password_is_rejected(client, db_available):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice.perera@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_login_as_staff_via_customer_endpoint_fails(client, db_available):
    # /api/v1/auth/login only ever matches role == "customer" (see
    # routers/public/auth.py) — staff/super_admin must use the admin
    # instance's /api/v1/auth/login instead. This guards against that
    # separation regressing.
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "staff.kasun@rentease.com", "password": "Staff@123"},
    )
    assert resp.status_code == 401


def test_items_catalog_is_publicly_listable(client, db_available):
    resp = client.get("/api/v1/items")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
