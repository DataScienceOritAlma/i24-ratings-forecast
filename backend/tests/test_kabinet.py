"""Kabinet Shishi prediction rules — שלב 101.

Each test pins one of the faults found when the saved predictions were compared
with the ratings that actually came in (April–October 2026).
"""
import datetime as dt
from unittest.mock import MagicMock, patch

import pytest

VALID_USER = MagicMock(status_code=200, json=lambda: {"id": "fake-uid", "email": "tester@example.com"})
AUTH = {"Authorization": "Bearer valid.fake.token"}


def _predict(client, body, **overrides):
    with patch("main.requests.get", return_value=VALID_USER):
        return client.post("/predict", headers=AUTH, json={**body, **overrides})


def test_non_friday_is_rejected(client, predict_body):
    """2026-10-19 is a Monday; the old model answered 4.62 for it."""
    r = _predict(client, predict_body, target_date="2026-10-19")
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "שישי" in detail and "23/10/2026" in detail, detail


def test_prediction_is_raw_rating(client, predict_body):
    body = _predict(client, predict_body).json()
    assert body["target_kind"] == "raw"
    assert body["predicted_rating_raw"] is None and body["reception_pct_used"] is None


def test_no_trend_inflation_for_far_dates(client, predict_body):
    """The removed trend multiplier added ~5% per month to far-off dates."""
    near = _predict(client, predict_body, target_date="2027-01-08").json()
    far = _predict(client, predict_body, target_date="2027-07-09").json()
    assert near["predicted_rating"] == far["predicted_rating"]
    assert far["metadata"]["days_ahead"] > near["metadata"]["days_ahead"] > 0


def test_interval_comes_from_backtest_errors(client, predict_body):
    import main
    body = _predict(client, predict_body, target_date="2027-01-08").json()
    width = body["prediction_high"] - body["prediction_low"]
    assert width == pytest.approx(2 * main.HALF_WIDTH["routine"], abs=0.002)
    # ±1.36 (the old y_std interval) covered every outcome and so said nothing
    assert main.HALF_WIDTH["routine"] < 1.2


def test_holiday_friday_carries_a_warning(client, predict_body):
    eve = _predict(client, predict_body, target_date="2027-10-01").json()
    assert "ראש השנה" in eve["metadata"]["holiday_warning"]
    plain = _predict(client, predict_body, target_date="2027-01-08").json()
    assert plain["metadata"]["holiday_warning"] is None


def test_security_scenario_needs_an_active_event(client, predict_body):
    """special_event on a quiet date must equal routine; inside a known event it must not."""
    quiet_r = _predict(client, predict_body, target_date="2027-01-08").json()
    quiet_s = _predict(client, predict_body, target_date="2027-01-08", scenario="special_event").json()
    assert quiet_s["predicted_rating"] == quiet_r["predicted_rating"]
    assert quiet_s["metadata"]["scenario_effective"] == "routine"

    war_r = _predict(client, predict_body, target_date="2026-03-13").json()
    war_s = _predict(client, predict_body, target_date="2026-03-13", scenario="special_event").json()
    assert war_s["metadata"]["event_active_on_date"] is True
    assert war_s["predicted_rating"] > war_r["predicted_rating"]
    assert war_s["prediction_high"] - war_s["prediction_low"] >= war_r["prediction_high"] - war_r["prediction_low"]


def test_history_holds_one_live_friday_per_date():
    import main
    h = main.KABINET_HISTORY
    assert h["תאריך שידור"].is_unique
    assert (h["תאריך שידור"].dt.weekday == main.FRIDAY).all()
    assert (h["שם תוכנית"].str.strip() == main.SCOPE_PROGRAM_NAME).all()


@pytest.mark.parametrize("value, expected", [
    (dt.time(19, 50, 7), "19:50:07"),
    (dt.timedelta(days=1, minutes=23, seconds=36), "24:23:36"),   # '1 day, 0:23:36'
    (dt.datetime(1900, 1, 1, 1, 27, 46), "25:27:46"),             # Excel time past 24h
    ("06:11:29", "06:11:29"),
    ("24:00:00", "24:00:00"),
    (None, None),
])
def test_canon_time_gives_one_spelling(value, expected):
    from process_raw_data import canon_time
    assert canon_time(value) == expected
