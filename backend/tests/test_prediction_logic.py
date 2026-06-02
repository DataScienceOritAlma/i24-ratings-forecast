"""Pure unit tests for the prediction_logic helpers — no Supabase, no FastAPI."""
from datetime import date, time

import pytest


def test_estimate_reception_pct_in_known_range():
    """reception_pct is bounded to roughly [0.65, 0.95] over the project window."""
    from prediction_logic import estimate_reception_pct

    # A date squarely inside the training window
    p = estimate_reception_pct(date(2025, 12, 1))
    assert 0.60 <= p <= 0.95


def test_estimate_reception_pct_extrapolates_forward_capped():
    """Far future date should still return a sane value (no crash, no negative)."""
    from prediction_logic import estimate_reception_pct

    p = estimate_reception_pct(date(2027, 1, 1))
    assert 0.0 < p <= 1.0


def test_date_to_weekday_he_returns_hebrew():
    """The helper returns Hebrew day names that downstream code expects."""
    from prediction_logic import date_to_weekday_he

    # 2026-06-05 is a Friday
    wd = date_to_weekday_he(date(2026, 6, 5))
    assert wd in {"ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"}


def test_rating_to_viewers_monotonic():
    """Higher rating → more viewers (households increase with rating)."""
    from prediction_logic import rating_to_viewers

    low = rating_to_viewers(0.2)
    high = rating_to_viewers(2.0)
    assert high["households"] > low["households"]
    assert high["viewers"] > low["viewers"]


def test_rating_to_viewers_returns_ints():
    """Households/viewers must be integers for the API contract."""
    from prediction_logic import rating_to_viewers

    out = rating_to_viewers(1.5)
    assert isinstance(out["households"], int)
    assert isinstance(out["viewers"], int)
