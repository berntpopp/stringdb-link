"""Security guard for CORS credentials on the unauthenticated backend.

This backend holds no cookies or sessions, so ``allow_credentials`` is
meaningless and must default to ``False``. A credentialed wildcard origin is
forbidden by the CORS spec and rejected by browsers, so the app must fail
closed at startup if that combination is ever configured. Preserving the full
method list (GET/POST/PUT/DELETE/OPTIONS) keeps GET ``/health`` reachable.

Research use only; not clinical decision support."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from stringdb_link import app as app_module
from stringdb_link.config_models import CORSConfigModel


def test_cors_credentials_disabled_by_default() -> None:
    """Credentials are off by default (backend is unauthenticated)."""
    assert CORSConfigModel().allow_credentials is False


def test_health_endpoint_still_returns_200() -> None:
    """GET /health stays 200 — the method list is preserved, not POST-only."""
    client = TestClient(app_module.create_app())
    response = client.get("/health")
    assert response.status_code == 200


def test_startup_guard_rejects_credentials_with_wildcard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed if allow_credentials=True is combined with a '*' origin."""
    monkeypatch.setattr(app_module.settings.cors, "allow_credentials", True)
    monkeypatch.setattr(app_module.settings.cors, "allow_origins", ["*"])
    with pytest.raises(ValueError, match="wildcard"):
        app_module.create_app()
