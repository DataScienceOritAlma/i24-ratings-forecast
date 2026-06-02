"""Smoke tests for /health and /."""


def test_health_open(client):
    """/health must be reachable without auth (used by keep-alive cron)."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "model" in body
    # History is loaded — we expect thousands of rows
    assert body["history_rows"] > 1000
    assert "expected_mae" in body


def test_root_endpoint_describes_service(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "i24-ratings-forecast"
    assert "/predict (POST)" in body["endpoints"]


def test_security_headers_present(client):
    """Every response carries the hardened header set (שלב 88)."""
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in r.headers
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
