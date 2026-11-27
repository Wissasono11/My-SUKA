"""Uji kit keamanan layanan (microapp-kit/python) dan kompatibilitasnya dengan portal-api yang sebenarnya."""
import sys
import time
import uuid
from pathlib import Path

import fakeredis
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "microapp-kit" / "python"))
import mysuka_sso as kit  # noqa: E402
from example_fastapi import create_app  # noqa: E402

ISS, SVC = "https://mysuka.test", "sukaketemu"
SECRET = "k" * 40


def make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


PORTAL, ATTACKER = make_key(), make_key()


class StubJWKS:
    """Meniru PyJWKClient: hanya kid 'portal-1' yang dikenal."""
    def get_signing_key_from_jwt(self, token):
        if jwt.get_unverified_header(token).get("kid") != "portal-1":
            raise jwt.PyJWKClientError("kid tidak dikenal")
        return type("K", (), {"key": PORTAL.public_key()})()


def cfg(**kw):
    base = dict(service_id=SVC, issuer=ISS, jwks_url=f"{ISS}/.well-known/jwks.json", exchange_url=f"{ISS}/api/sso/exchange", client_secret=SECRET, production=True)
    return kit.SsoConfig(**{**base, **kw})


def verifier(**kw):
    return kit.Verifier(cfg(), jwks_client=StubJWKS(), **kw)


def tok(typ="handoff", key=PORTAL, alg="RS256", kid="portal-1", headers=None, **over):
    now = int(time.time())
    p = {"iss": ISS, "aud": SVC, "iat": now, "exp": now + 60, "jti": uuid.uuid4().hex, "sub": "usr_abc", "sid": "sid_abc",
         "typ": typ, "svc": SVC, "user": {"id": "usr_abc", "primary_role": "MAHASISWA"}}
    p.update(over)
    p = {k: v for k, v in p.items() if v is not None}
    return jwt.encode(p, key, algorithm=alg, headers={"kid": kid, **(headers or {})})


def logout_tok(**over):
    now = int(time.time())
    p = {"iss": ISS, "aud": SVC, "iat": now, "exp": now + 60, "jti": uuid.uuid4().hex, "sub": "usr_abc", "sid": "sid_abc", "events": {kit.BACKCHANNEL_EVENT: {}}}
    p.update(over)
    p = {k: v for k, v in p.items() if v is not None}
    return jwt.encode(p, PORTAL, algorithm="RS256", headers={"kid": "portal-1", "typ": "logout+jwt"})


# ----------------------------------------------------------------------------- handoff
def test_handoff_sah_dan_sekali_pakai():
    v, t = verifier(), tok()
    c = v.verify_handoff(t)
    assert c.sub == "usr_abc" and c.sid == "sid_abc" and c.role == "MAHASISWA"
    with pytest.raises(kit.SsoError, match="replay"):
        v.verify_handoff(t)


def forged_hs256():
    pem = PORTAL.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    now = int(time.time())
    # PyJWT menolak memakai PEM sebagai kunci HMAC; bangun token HS256 manual seperti penyerang sungguhan.
    import base64, hashlib, hmac, json
    b = lambda d: base64.urlsafe_b64encode(d).rstrip(b"=")
    head = b(json.dumps({"alg": "HS256", "typ": "JWT", "kid": "portal-1"}).encode())
    body = b(json.dumps({"iss": ISS, "aud": SVC, "iat": now, "exp": now + 60, "jti": "j" * 32, "sub": "usr_x", "sid": "s", "typ": "handoff", "svc": SVC}).encode())
    sig = b(hmac.new(pem, head + b"." + body, hashlib.sha256).digest())
    return (head + b"." + body + b"." + sig).decode()


def none_alg():
    import base64, json
    b = lambda d: base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    now = int(time.time())
    return b(json.dumps({"alg": "none", "typ": "JWT"}).encode()) + "." + b(json.dumps({"iss": ISS, "aud": SVC, "iat": now, "exp": now + 60, "jti": "j" * 32, "sub": "u", "sid": "s", "typ": "handoff", "svc": SVC}).encode()) + "."


@pytest.mark.parametrize("name,token", [
    ("alg none", none_alg()),
    ("HS256 dengan kunci publik sebagai rahasia", forged_hs256()),
    ("ditandatangani penyerang", tok(key=ATTACKER)),
    ("kid tak dikenal", tok(kid="evil")),
    ("aud layanan lain", tok(aud="paas", svc="paas")),
    ("aud daftar memuat layanan lain", tok(aud=[SVC, "paas"])),
    ("iss lain", tok(iss="https://evil.example")),
    ("typ widget dipakai sebagai handoff", tok(typ="widget")),
    ("typ session dipakai sebagai handoff", tok(typ="session", aud="mysuka-portal")),
    ("svc layanan lain", tok(svc="paas")),
    ("kedaluwarsa", tok(iat=int(time.time()) - 400, exp=int(time.time()) - 200)),
    ("umur terlalu panjang", tok(exp=int(time.time()) + 86400)),
    ("tanpa jti", tok(jti=None)),
    ("tanpa sid", tok(sid=None)),
    ("tanpa exp", tok(exp=None)),
    ("sampah", "bukan.jwt.sama-sekali"),
    ("terlalu panjang", "a" * 9000),
    ("kosong", ""),
])
def test_handoff_palsu_ditolak(name, token):
    with pytest.raises(kit.SsoError):
        verifier().verify_handoff(token)


def test_widget_tidak_sekali_pakai_tetapi_typ_dan_svc_dikunci():
    v, t = verifier(), tok(typ="widget")
    assert v.verify_widget(t).sub == "usr_abc" and v.verify_widget(t).sub == "usr_abc"
    with pytest.raises(kit.SsoError):
        v.verify_widget(tok(typ="handoff"))
    with pytest.raises(kit.SsoError):
        v.verify_widget(tok(typ="widget", svc="paas"))


# ----------------------------------------------------------------------------- logout token
def test_logout_token_sah_dan_replay_ditolak():
    v, t = verifier(), logout_tok()
    assert v.verify_logout(t).sid == "sid_abc"
    with pytest.raises(kit.SsoError, match="replay"):
        v.verify_logout(t)


@pytest.mark.parametrize("over", [{"events": {}}, {"events": None}, {"nonce": "x"}, {"sid": None}, {"aud": "paas"}])
def test_logout_token_cacat_ditolak(over):
    with pytest.raises(kit.SsoError):
        verifier().verify_logout(logout_tok(**over))


def test_logout_token_wajib_typ_header_logout_jwt_dan_handoff_bukan_logout():
    with pytest.raises(kit.SsoError, match="typ header"):
        verifier().verify_logout(tok(typ="handoff", events={kit.BACKCHANNEL_EVENT: {}}))  # typ header JWT biasa
    with pytest.raises(kit.SsoError):
        verifier().verify_handoff(logout_tok())  # logout token tidak boleh jadi login


# ----------------------------------------------------------------------------- konfigurasi, cookie, helper
def test_config_menolak_rahasia_pendek_dan_http_di_produksi():
    with pytest.raises(kit.SsoError):
        cfg(client_secret="pendek").validate()
    with pytest.raises(kit.SsoError, match="https"):
        cfg(issuer="http://mysuka.example").validate()
    cfg(issuer="http://localhost:8000", jwks_url="http://localhost:8000/j", exchange_url="http://localhost:8000/e").validate()
    with pytest.raises(kit.SsoError, match="belum lengkap"):
        kit.SsoConfig.from_env({})


def test_cookie_sesi_host_only_di_produksi():
    name, kw = kit.session_cookie(cfg())
    assert name == "__Host-session" and kw == {"httponly": True, "secure": True, "samesite": "lax", "path": "/"} and "domain" not in kw
    assert kit.session_cookie(cfg(production=False))[0] == "session"


def test_safe_next_dan_header_sensitif():
    assert kit.safe_next("/a?b=1") == "/a?b=1"
    for bad in ("//evil.example", "https://evil.example", "/\\evil", "/a\nb", None, ""):
        assert kit.safe_next(bad, "/x") == "/x"
    h = kit.security_headers(sensitive=True)
    assert h["Cache-Control"] == "no-store" and h["Referrer-Policy"] == "same-origin" and "frame-ancestors 'none'" in h["Content-Security-Policy"]


def test_pkce_cocok_dengan_portal():
    from app import google
    verifier_, challenge = kit.new_pkce()
    assert google.pkce_challenge(verifier_) == challenge and len(challenge) == 43


def test_exchange_code_menolak_respons_tak_sah_dan_tidak_mengikuti_redirect():
    seen = {}

    def post(url, json, timeout, follow_redirects):
        seen.update(url=url, follow=follow_redirects, body=json)
        return type("R", (), {"status_code": 200, "json": lambda self: {"token": "t", "token_type": "Bearer"}})()

    assert kit.exchange_code(cfg(), "c" * 30, "v" * 50, post=post) == "t"
    assert seen["follow"] is False and seen["body"]["client_secret"] == SECRET and seen["body"]["client_id"] == SVC
    with pytest.raises(kit.SsoError):
        kit.exchange_code(cfg(), "pendek")
    for status, payload in ((401, {}), (200, {"token": "t"}), (200, [])):
        bad = lambda url, json, timeout, follow_redirects, s=status, p=payload: type("R", (), {"status_code": s, "json": lambda self: p})()
        with pytest.raises(kit.SsoError):
            kit.exchange_code(cfg(), "c" * 30, post=bad)

    def boom(*a, **k):
        raise TimeoutError("lambat")
    with pytest.raises(kit.SsoError, match="exchange gagal"):
        kit.exchange_code(cfg(), "c" * 30, post=boom)


def test_replay_cache_redis_dan_memori():
    for cache in (kit.MemoryReplayCache(), kit.RedisReplayCache(fakeredis.FakeRedis())):
        assert cache.seen_before("a", 30) is False
        assert cache.seen_before("a", 30) is True
        assert cache.seen_before("b", 30) is False


def test_session_index_mengakhiri_semua_sesi_ber_sid_itu():
    idx, ended = kit.SessionIndex(), []
    idx.bind("l1", "s1"); idx.bind("l2", "s1"); idx.bind("l3", "s2")
    assert idx.end_by_portal_sid("s1", ended.append) == 2 and sorted(ended) == ["l1", "l2"]
    assert idx.end_by_portal_sid("s1", ended.append) == 0


# ----------------------------------------------------------------------------- integrasi: kit <-> portal-api nyata
@pytest.fixture
def flow(client, user, monkeypatch):
    """Layanan contoh (kit) yang bertukar kode dengan portal-api nyata di dalam proses yang sama."""
    from app.keys import load_keys
    from app.tokens import sign_token

    _, jwk = load_keys()

    class PortalJWKS:
        def get_signing_key_from_jwt(self, token):
            return jwt.PyJWK(jwk)

    def post(url, json, timeout, follow_redirects):
        assert url == "https://mysuka.test/api/sso/exchange" and follow_redirects is False
        return client.post("/api/sso/exchange", json=json)

    c = cfg(client_secret=("secret-sukaketemu-").ljust(40, "x"), production=True)
    svc_app = create_app(c, verifier=kit.Verifier(c, jwks_client=PortalJWKS()), post=post)
    svc = TestClient(svc_app, base_url="https://mysuka.test", follow_redirects=False)
    client.cookies.set("mysuka_session", sign_token(user, 3600))
    return client, svc, sign_token, user


def start(client, svc):
    r = svc.get("/sukaketemu/sso-start")
    assert r.status_code == 302 and "code_challenge=" in r.headers["location"]
    challenge = r.headers["location"].split("code_challenge=")[1].split("&")[0]
    launched = client.get("/api/sso/launch", params={"app": "sukaketemu", "code_challenge": challenge, "code_challenge_method": "S256"})
    return launched.headers["location"].split("code=")[1]


def test_alur_penuh_pkce_sesi_lokal_widget_dan_logout(flow):
    client, svc, sign_token, user = flow
    from app.tokens import decode_session, sign_logout_token

    code = start(client, svc)
    cb = svc.get("/sukaketemu/sso-callback", params={"code": code})
    assert cb.status_code == 303 and cb.headers["cache-control"] == "no-store"
    sc = cb.headers["set-cookie"]
    assert sc.startswith("__Host-session=") and "HttpOnly" in sc and "Secure" in sc and "Domain" not in sc
    me = svc.get("/sukaketemu/me").json()
    assert me["id"].startswith("usr_") and me["role"] == "MAHASISWA"
    assert svc.get("/sukaketemu/me", headers={"x-frame-options": "x"}).headers["x-frame-options"] == "DENY"

    # kode sekali pakai: callback kedua dengan kode yang sama gagal dan tidak memberi sesi baru
    svc.cookies.clear()
    again = svc.get("/sukaketemu/sso-callback", params={"code": code})
    assert again.status_code == 401 and "set-cookie" not in again.headers

    # widget: token benar diterima, token untuk layanan lain ditolak (aud)
    own = sign_token(user, 60, service="sukaketemu", purpose="widget")
    other = sign_token(user, 60, service="paas", purpose="widget")
    ok = svc.get("/sukaketemu/api/widget/summary", headers={"authorization": f"Bearer {own}"})
    assert ok.status_code == 200 and ok.json()["status"] == "success"
    assert svc.get("/sukaketemu/api/widget/summary", headers={"authorization": f"Bearer {other}"}).status_code == 401
    assert svc.get("/sukaketemu/api/widget/summary").status_code == 401

    # back-channel logout dari portal mengakhiri sesi lokal
    svc2 = svc
    code2 = start(client, svc2)
    cb2 = svc2.get("/sukaketemu/sso-callback", params={"code": code2})
    assert svc2.get("/sukaketemu/me").status_code == 200
    session = decode_session(client.cookies.get("mysuka_session"))
    from app.tokens import sign_logout_token as slt
    lt = slt(session["user"], session["sid"], "sukaketemu")
    assert svc2.post("/sukaketemu/api/backchannel-logout", data={"logout_token": lt}).status_code == 200
    assert svc2.get("/sukaketemu/me").status_code == 401
    # logout token yang sama tidak bisa diputar ulang
    assert svc2.post("/sukaketemu/api/backchannel-logout", data={"logout_token": lt}).status_code == 400


def test_callback_tanpa_code_dan_mode_token_lama_ditolak(flow):
    _, svc, sign_token, user = flow
    assert svc.get("/sukaketemu/sso-callback").status_code == 400
    legacy = sign_token(user, 60, service="sukaketemu")
    r = svc.get("/sukaketemu/sso-callback", params={"token": legacy})
    assert r.status_code == 400 and "set-cookie" not in r.headers
    r = svc.get("/sukaketemu/sso-callback", params={"code": "x" * 30, "next": "https://evil.example"})
    assert r.status_code == 401 and "location" not in r.headers
