import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import keys, security, widgets
from app.deps import http_client
from app.main import app


@pytest.fixture(autouse=True)
def env(monkeypatch):
    for k in ("ENV", "SSO_PRIVATE_KEY_PEM", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "ADMIN_EMAILS", "IDENTITY_HMAC_SECRET", "PRIVACY_SERVICES", "SESSION_COOKIE_NAME"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("APP_BASE_URL", "https://mysuka.test")
    monkeypatch.setenv("SUKAKETEMU_ORIGIN", "https://sukaketemu.upstream")
    monkeypatch.setenv("SISKA_ORIGIN", "https://siska.upstream")
    keys._load.cache_clear()
    security.reset_rate_limits()
    widgets.reset_widget_cache()
    yield
    app.dependency_overrides.clear()


GOOD_WIDGET = {"status": "success", "data": {
    "summary_title": "Status", "active_count": 2, "count_label": "Laporan Aktif", "badge_label": "1 Kecocokan Baru!",
    "recent_items": [{"id": "r1", "title": "KTM", "subtitle": "Pos Satpam", "updated_at": "2026-11-20T10:15:00Z"}],
    "action_url": "/sukaketemu/dashboard"}}


@pytest.fixture
def calls():
    return []


@pytest.fixture
def client(calls):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.host == "sukaketemu.upstream":
            return httpx.Response(200, json=GOOD_WIDGET)
        return httpx.Response(404)

    mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app.dependency_overrides[http_client] = lambda: mock
    with TestClient(app, base_url="https://mysuka.test", follow_redirects=False) as c:
        yield c


@pytest.fixture
def user():
    from app.tokens import derive_user
    return {**derive_user("23106050059@student.uin-suka.ac.id", "Radinka Rafie"), "faculty": "SAINTEK", "department": "Informatika"}


@pytest.fixture
def session_cookie(user):
    from app.tokens import sign_token
    return {"mysuka_session": sign_token(user, 3600)}


def decode_unverified(token):
    import jwt
    return jwt.decode(token, options={"verify_signature": False}), jwt.get_unverified_header(token)
