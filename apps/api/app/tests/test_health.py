"""
Smoke tests that don't touch the database — these should pass in any
environment, including a bare `pip install -r requirements.txt && pytest`
with no MySQL running, since they're what CI uses as the fast first gate
before the DB-backed integration tests.
"""


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["mode"] == "public"


def test_public_mode_has_no_admin_routes(client):
    # api-public must never expose /api/v1/admin/* — see main.py's
    # APP_MODE branch and RentEase_Architecture.md Section 0/4.
    resp = client.get("/api/v1/admin/staff")
    assert resp.status_code == 404


def test_unauthenticated_me_is_rejected(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)
