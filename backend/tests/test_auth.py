"""Auth (JWT validation) tests — שלב 87.

The require_user() dependency calls Supabase's /auth/v1/user. We DON'T want
the test suite to hit Supabase over the network, so we patch the requests.get
call before the protected endpoints are invoked.
"""
from unittest.mock import patch, MagicMock


def test_predict_rejects_missing_auth(client, predict_body):
    r = client.post("/predict", json=predict_body)
    assert r.status_code == 401
    assert "Missing" in r.json()["detail"]


def test_predict_rejects_malformed_header(client, predict_body):
    r = client.post(
        "/predict",
        headers={"Authorization": "notbearer xyz"},
        json=predict_body,
    )
    assert r.status_code == 401


def test_predict_rejects_empty_bearer(client, predict_body):
    r = client.post(
        "/predict",
        headers={"Authorization": "Bearer  "},
        json=predict_body,
    )
    assert r.status_code == 401


def test_predict_rejects_invalid_token(client, predict_body):
    """A token that's well-formed but rejected by Supabase -> 401."""
    # Supabase returns 401 for invalid/expired tokens; we mock the upstream.
    mocked = MagicMock(status_code=401, json=lambda: {"msg": "invalid token"})
    with patch("main.requests.get", return_value=mocked):
        r = client.post(
            "/predict",
            headers={"Authorization": "Bearer fake-but-wellformed.jwt.token"},
            json=predict_body,
        )
    assert r.status_code == 401
    assert "Invalid" in r.json()["detail"]


def test_ask_also_locked(client):
    r = client.post("/ask", json={"question": "מה הצפי לקבינט שישי?"})
    assert r.status_code == 401


def test_predict_passes_with_valid_token(client, predict_body):
    """When Supabase says the token is valid, the prediction runs to completion."""
    mocked = MagicMock(
        status_code=200,
        json=lambda: {"id": "fake-uid", "email": "tester@example.com"},
    )
    with patch("main.requests.get", return_value=mocked):
        r = client.post(
            "/predict",
            headers={"Authorization": "Bearer valid.fake.token"},
            json=predict_body,
        )
    assert r.status_code == 200, r.text
    body = r.json()
    # Core fields present
    assert "predicted_rating" in body
    assert "prediction_low" in body
    assert "prediction_high" in body
    # Quantile interval should be in use (שלב 78)
    assert body["uncertainty_source"] in ("conformal_quantile", "slot_std", "slot_std_fallback")
    # Asymmetric interval expected when quantile_obj loaded
    assert body["prediction_low"] <= body["predicted_rating"] <= body["prediction_high"]
