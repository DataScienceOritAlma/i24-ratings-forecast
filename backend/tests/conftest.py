"""Shared pytest fixtures.

Loads the FastAPI app once per test session (model + history load is ~10s)
and exposes it as a TestClient. Auth is enforced — tests pass a Bearer
token explicitly or call /health (which is open).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make `backend/` importable as a top-level package for the test process.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def app():
    """Import the app once and re-use across all tests in the session."""
    from main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    return TestClient(app)


@pytest.fixture
def predict_body() -> dict:
    """A valid PredictRequest payload — used by multiple tests."""
    return {
        "program_name": "קבינט שישי",
        "target_date": "2026-06-05",
        "start_time": "19:50:00",
        "end_time": "22:00:00",
        "scenario": "routine",
        "status": "שידור חי",
    }
