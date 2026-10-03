"""Unit/API tests isolate lifecycle; run_live_checks.py exercises real MongoDB."""
from contextlib import asynccontextmanager
import pytest
from app.main import app


@asynccontextmanager
async def isolated_lifespan(application):
    yield


@pytest.fixture(autouse=True)
def isolate_unit_lifecycle(monkeypatch):
    monkeypatch.setattr(app.router, 'lifespan_context', isolated_lifespan)
