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
    # שלב 83 החליף הודעה כללית בהודעה שמוסרת מה Supabase ענה, כדי שתקלת
    # הגדרה ב-Render לא תיראה כמו משתמש לא מורשה. זה מה שנבדק כאן: גם
    # הסטטוס שחזר מלמעלה וגם הנימוק חייבים להופיע בהודעה.
    detail = r.json()["detail"]
    assert "401" in detail and "invalid token" in detail, detail


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
    # מקור אי-הוודאות: מאז שלב 98 קבינט שישי רץ על מודל ייעודי, והרווח נגזר
    # מ-y_std שלו. הבדיקה הישנה עוד ציפתה לשמות מלפני כן, ולכן נכשלה אף
    # שהקוד תקין. נבדק כאן מה שבאמת חייב להתקיים: השדה מלא, הוא אחד
    # מהמקורות המוכרים, והוא זהה למה שמדווח ב-metadata.
    known_sources = ("y_std_kabinet", "conformal_quantile", "slot_std", "slot_std_fallback")
    assert body["uncertainty_source"] in known_sources, body["uncertainty_source"]
    assert body["metadata"]["interval_method"] == body["uncertainty_source"]
    # הרווח חייב להקיף את התחזית
    assert body["prediction_low"] <= body["predicted_rating"] <= body["prediction_high"]
    assert body["prediction_low"] < body["prediction_high"], "a zero-width interval is not an interval"
