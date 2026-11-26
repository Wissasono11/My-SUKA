import base64
import hashlib

import httpx
import jwt
import pytest
from starlette.testclient import TestClient

from app import store
from app.keys import load_keys
from app.main import app
from app.deps import http_client
from tests.conftest import decode_unverified, secret_of


def launch(client, session_cookie, service="sukaketemu", **params):
    client.cookies.update(session_cookie)
    r = client.get("/api/sso/launch", params={"app": service, **params})
    return r.headers["location"].split("code=")[1]


def exchange(client, code, service="sukaketemu", secret=None, **extra):
    return client.post("/api/sso/exchange", json={"code": code, "client_id": service, "client_secret": secret or secret_of(service), **extra})


def pkce(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


def test_kode_ditukar_jadi_jwt_pendek_beraudience_layanan(client, session_cookie, user):
    code = launch(client, session_cookie)
    r = exchange(client, code)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    payload, header = decode_unverified(body["token"])
    assert body["token_type"] == "Bearer" and body["expires_in"] == 60
    assert payload["aud"] == "sukaketemu" and payload["typ"] == "handoff" and payload["svc"] == "sukaketemu"
    assert payload["exp"] - payload["iat"] == 60 and len(payload["jti"]) == 32
    assert payload["sid"].startswith("sid_") and header["alg"] == "RS256"
    _, jwk = load_keys()
    jwt.decode(body["token"], jwt.PyJWK(jwk).key, algorithms=["RS256"], audience="sukaketemu", issuer="https://mysuka.test")


def test_kode_hanya_berlaku_sekali(client, session_cookie):
    code = launch(client, session_cookie)
    assert exchange(client, code).status_code == 200
    r = exchange(client, code)
    assert r.status_code == 400 and r.json() == {"error": "invalid_grant"}


def test_kode_kedaluwarsa_ditolak(client, session_cookie, monkeypatch):
    code = launch(client, session_cookie)
    real = store._now()
    monkeypatch.setattr(store, "_now", lambda: real + 31)
    assert exchange(client, code).status_code == 400


def test_kode_terikat_ke_layanan_dan_terbakar_bila_dipakai_layanan_lain(client, session_cookie):
    code = launch(client, session_cookie, "sukaketemu")
    assert exchange(client, code, "campusfix").status_code == 400
    assert exchange(client, code, "sukaketemu").status_code == 400  # sudah terbakar


def test_rahasia_client_salah_atau_layanan_tak_dikenal_401(client, session_cookie):
    code = launch(client, session_cookie)
    assert exchange(client, code, secret="x" * 40).status_code == 401
    assert exchange(client, code, "nope").status_code == 401
    assert exchange(client, code).status_code == 200, "kode tidak terbakar oleh kegagalan autentikasi client"


def test_tebakan_rahasia_dibatasi(client, session_cookie):
    codes = [exchange(client, "c" * 30, secret="x" * 40).status_code for _ in range(12)]
    assert codes[:10] == [401] * 10 and codes[10:] == [429, 429]


def test_pkce_wajib_cocok_bila_challenge_dikirim(client, session_cookie):
    verifier = "v" * 64
    code = launch(client, session_cookie, code_challenge=pkce(verifier), code_challenge_method="S256")
    assert exchange(client, code).status_code == 400  # tanpa verifier
    code = launch(client, session_cookie, code_challenge=pkce(verifier), code_challenge_method="S256")
    assert exchange(client, code, code_verifier="w" * 64).status_code == 400
    code = launch(client, session_cookie, code_challenge=pkce(verifier), code_challenge_method="S256")
    assert exchange(client, code, code_verifier=verifier).status_code == 200


def test_challenge_tidak_valid_ditolak(client, session_cookie):
    client.cookies.update(session_cookie)
    assert client.get("/api/sso/launch", params={"app": "paas", "code_challenge": "pendek", "code_challenge_method": "S256"}).status_code == 400
    assert client.get("/api/sso/launch", params={"app": "paas", "code_challenge": "a" * 43, "code_challenge_method": "plain"}).status_code == 400


def test_token_serah_terima_tidak_bisa_jadi_cookie_sesi(client, session_cookie):
    token = exchange(client, launch(client, session_cookie)).json()["token"]
    client.cookies.clear()
    client.cookies.set("mysuka_session", token)
    assert client.get("/api/widget/summary").status_code == 401
    assert client.get("/api/sso/session").status_code == 401


def test_token_sesi_tidak_diterima_untuk_audience_layanan(user):
    from app.tokens import sign_token
    payload, _ = decode_unverified(sign_token(user, 60))
    assert payload["aud"] == "mysuka-portal" and payload["typ"] == "session" and len(payload["sid"]) == 32


def test_token_widget_hanya_id_dan_peran(user):
    from app.tokens import sign_token
    payload, _ = decode_unverified(sign_token(user, 60, service="sukaketemu", purpose="widget"))
    assert payload["typ"] == "widget" and set(payload["user"]) == {"id", "primary_role"}


def test_sid_berbeda_per_layanan_agar_tak_bisa_dikorelasikan(client, session_cookie):
    a = decode_unverified(exchange(client, launch(client, session_cookie, "sukaketemu")).json()["token"])[0]["sid"]
    b = decode_unverified(exchange(client, launch(client, session_cookie, "siska"), "siska").json()["token"])[0]["sid"]
    assert a != b


def test_logout_mencabut_sesi_di_server_walau_cookie_dicuri(client, session_cookie):
    client.cookies.update(session_cookie)
    assert client.get("/api/sso/session").status_code == 200
    assert client.post("/api/sso/logout", headers={"origin": "https://mysuka.test"}).status_code == 303
    client.cookies.update(session_cookie)  # penyerang memutar ulang cookie lama
    assert client.get("/api/sso/session").status_code == 401
    assert client.get("/api/widget/summary").status_code == 401
    assert client.get("/api/sso/launch", params={"app": "sukaketemu"}).headers["location"].startswith("https://mysuka.test/login")


def test_logout_mengirim_back_channel_logout_token(session_cookie, monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    monkeypatch.setenv("SUKAKETEMU_BACKCHANNEL_LOGOUT_URL", "https://sukaketemu.upstream/sukaketemu/api/backchannel-logout")
    mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app.dependency_overrides[http_client] = lambda: mock
    with TestClient(app, base_url="https://mysuka.test", follow_redirects=False) as c:
        c.cookies.update(session_cookie)
        assert c.post("/api/sso/logout", headers={"origin": "https://mysuka.test"}).status_code == 303
    assert len(seen) == 1 and str(seen[0].url).endswith("/backchannel-logout")
    token = seen[0].content.decode().split("logout_token=")[1]
    payload, header = decode_unverified(token)
    assert header["typ"] == "logout+jwt" and payload["aud"] == "sukaketemu"
    assert "http://schemas.openid.net/event/backchannel-logout" in payload["events"] and "nonce" not in payload
    assert payload["sid"].startswith("sid_") and payload["exp"] - payload["iat"] == 60
    _, jwk = load_keys()
    jwt.decode(token, jwt.PyJWK(jwk).key, algorithms=["RS256"], audience="sukaketemu", issuer="https://mysuka.test")


def test_jwks_memuat_kunci_lama_saat_rotasi_dan_menolak_kunci_privat(client, monkeypatch):
    import json
    from app.keys import load_jwks
    retired = {"kty": "RSA", "kid": "mysuka-superapp-key-2026-v0", "n": "abc", "e": "AQAB"}
    monkeypatch.setenv("SSO_RETIRED_JWKS", json.dumps([retired]))
    kids = [k["kid"] for k in client.get("/.well-known/jwks.json").json()["keys"]]
    assert kids == ["mysuka-superapp-key-2026-v1", "mysuka-superapp-key-2026-v0"]
    monkeypatch.setenv("SSO_RETIRED_JWKS", json.dumps([{**retired, "d": "rahasia"}]))
    with pytest.raises(RuntimeError, match="PRIVAT"):
        load_jwks()


def test_header_keamanan_api(client):
    r = client.get("/api/widget/summary")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"


def test_validate_startup_produksi(monkeypatch):
    from app.config import get_settings, validate_startup
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SISKA_PUBLIC_ORIGIN", "http://siska.mysuka.test")
    with pytest.raises(RuntimeError, match="PUBLIC_ORIGIN"):
        validate_startup(get_settings(), ["siska"])
    monkeypatch.setenv("SISKA_PUBLIC_ORIGIN", "https://siska.mysuka.test/siska")
    with pytest.raises(RuntimeError, match="PUBLIC_ORIGIN"):
        validate_startup(get_settings(), ["siska"])
    monkeypatch.setenv("SISKA_PUBLIC_ORIGIN", "https://siska.mysuka.test")
    monkeypatch.delenv("SSO_CLIENT_SECRET_SISKA")
    assert any("SSO_CLIENT_SECRET_SISKA" in w for w in validate_startup(get_settings(), ["siska"]))
    monkeypatch.setenv("SISKA_BACKCHANNEL_LOGOUT_URL", "http://x/y")
    with pytest.raises(RuntimeError, match="https"):
        validate_startup(get_settings(), ["siska"])
