"""Pengerasan keamanan: ENV aman-secara-bawaan, sesi allowlist + idle, Redis, kebijakan PKCE, rotasi rahasia,
batas widget, log audit tanpa data pribadi, dan header API."""
import json
import logging

import fakeredis
import httpx
import pytest

from app import audit, security, store, widgets
from app.config import get_settings
from app.services import get_service
from app.tokens import derive_user, sign_token
from tests.conftest import GOOD_WIDGET, secret_of


def launch_code(client, app="sukaketemu", **params):
    r = client.get("/api/sso/launch", params={"app": app, **params})
    assert r.status_code == 302, r.text
    return r.headers["location"].split("code=")[1]


def exchange(client, code, app="sukaketemu", secret=None, **extra):
    return client.post("/api/sso/exchange", json={"code": code, "client_id": app, "client_secret": secret or secret_of(app), **extra})


# ----------------------------------------------------------------------------- ENV aman-secara-bawaan
def test_env_kosong_atau_salah_eja_dianggap_produksi(monkeypatch):
    monkeypatch.delenv("ENV")
    s = get_settings()
    assert s.production and s.session_cookie == "__Host-mysuka_session" and s.oidc_cookie == "__Host-mysuka_oidc"
    monkeypatch.setenv("ENV", "prod")  # salah eja => tetap ketat
    assert get_settings().production
    for ok in ("development", "test"):
        monkeypatch.setenv("ENV", ok)
        assert not get_settings().production


def test_login_dev_tidak_aktif_bila_env_kosong(client, monkeypatch):
    monkeypatch.delenv("ENV")
    monkeypatch.setenv("DEV_LOGIN", "1")
    assert client.get("/api/sso/login").headers["location"].endswith("error=config")


def test_cookie_oidc_produksi_host_prefix_secure_path_root(client, monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "sec")
    c = client.get("/api/sso/login").headers["set-cookie"]
    assert c.startswith("__Host-mysuka_oidc=") and "Secure" in c and "Path=/;" in c + ";" and "Domain" not in c and "HttpOnly" in c


def test_startup_produksi_menolak_http_dan_memperingatkan_tanpa_redis(monkeypatch):
    from app.config import validate_startup
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("APP_BASE_URL", "http://mysuka.test")
    with pytest.raises(RuntimeError, match="https"):
        validate_startup(get_settings(), ["sukaketemu"])
    monkeypatch.setenv("APP_BASE_URL", "https://mysuka.test")
    warnings = validate_startup(get_settings(), ["sukaketemu"])
    assert any("REDIS_URL" in w for w in warnings)


# ----------------------------------------------------------------------------- sesi: allowlist + idle + mutlak
def test_cookie_bertanda_tangan_sah_tetapi_tak_terdaftar_ditolak(client, user):
    token = sign_token(user, 3600)
    store.reset()  # mis. restart / sesi dihapus: tanda tangan benar tidak cukup
    client.cookies.set("mysuka_session", token)
    assert client.get("/api/sso/session").status_code == 401


def test_idle_timeout_dan_perpanjangan(client, session_cookie, monkeypatch):
    monkeypatch.setenv("SESSION_IDLE_SECONDS", "600")
    client.cookies.update(session_cookie)
    t0 = store._now()
    monkeypatch.setattr(store, "_now", lambda: t0 + 500)
    assert client.get("/api/sso/session").status_code == 200   # aktivitas memperpanjang idle
    monkeypatch.setattr(store, "_now", lambda: t0 + 1000)
    assert client.get("/api/sso/session").status_code == 200   # 500 dtk sejak aktivitas terakhir < 600
    monkeypatch.setattr(store, "_now", lambda: t0 + 1700)       # 700 dtk diam > 600
    assert client.get("/api/sso/session").status_code == 401
    monkeypatch.setattr(store, "_now", lambda: t0 + 1710)
    assert client.get("/api/sso/session").status_code == 401   # tidak hidup lagi


def test_batas_mutlak_tidak_bisa_diperpanjang_oleh_aktivitas(client, user, monkeypatch):
    token = sign_token(user, 1000)
    client.cookies.set("mysuka_session", token)
    t0 = store._now()
    for step in range(1, 10):
        monkeypatch.setattr(store, "_now", lambda step=step: t0 + step * 100)
        assert client.get("/api/sso/session").status_code == 200
    monkeypatch.setattr(store, "_now", lambda: t0 + 1001)
    assert client.get("/api/sso/session").status_code == 401


def test_logout_mencabut_sesi_cookie_curian_mati_dan_membersihkan_storage(client, session_cookie):
    client.cookies.update(session_cookie)
    stolen = dict(session_cookie)
    r = client.post("/api/sso/logout", headers={"origin": "https://mysuka.test"})
    assert 'storage' in r.headers["clear-site-data"]
    client.cookies.clear()
    client.cookies.update(stolen)
    assert client.get("/api/sso/session").status_code == 401


def test_exchange_ditolak_bila_sesi_berakhir_selama_kode_beredar(client, session_cookie):
    client.cookies.update(session_cookie)
    code = launch_code(client)
    client.post("/api/sso/logout", headers={"origin": "https://mysuka.test"})
    client.cookies.clear()
    r = exchange(client, code)
    assert r.status_code == 400 and r.json() == {"error": "invalid_grant"}


# ----------------------------------------------------------------------------- PKCE terkelola + rotasi rahasia
def pkce_pair():
    from app import google
    verifier = google.random_token(48)
    return verifier, google.pkce_challenge(verifier)


def test_layanan_wajib_pkce_dialihkan_ke_sso_start(client, session_cookie, monkeypatch):
    monkeypatch.setenv("SSO_PKCE_SERVICES", "siska")
    client.cookies.update(session_cookie)
    r = client.get("/api/sso/launch", params={"app": "siska"})
    assert r.status_code == 302 and r.headers["location"] == "https://mysuka.test/siska/sso-start"
    assert client.get("/api/sso/launch", params={"app": "paas"}).headers["location"].split("?")[0].endswith("/paas/sso-callback")


def test_layanan_wajib_pkce_menerima_challenge_dan_menolak_exchange_tanpa_verifier(client, session_cookie, monkeypatch):
    monkeypatch.setenv("SSO_PKCE_SERVICES", "siska")
    client.cookies.update(session_cookie)
    verifier, challenge = pkce_pair()
    code = launch_code(client, "siska", code_challenge=challenge, code_challenge_method="S256")
    assert exchange(client, code, "siska").status_code == 400  # tanpa verifier
    code = launch_code(client, "siska", code_challenge=challenge, code_challenge_method="S256")
    assert exchange(client, code, "siska", code_verifier=verifier).status_code == 200


def test_kode_lama_tanpa_challenge_ditolak_setelah_pkce_diwajibkan(client, session_cookie, monkeypatch):
    client.cookies.update(session_cookie)
    code = launch_code(client, "siska")  # dikeluarkan saat PKCE belum wajib
    monkeypatch.setenv("SSO_REQUIRE_PKCE", "1")
    assert exchange(client, code, "siska").status_code == 400


def test_rotasi_rahasia_client_dua_nilai_diterima(client, session_cookie, monkeypatch):
    nxt = "next-secret-".ljust(40, "n")
    monkeypatch.setenv("SSO_CLIENT_SECRET_SUKAKETEMU_NEXT", nxt)
    client.cookies.update(session_cookie)
    assert exchange(client, launch_code(client), secret=nxt).status_code == 200
    assert exchange(client, launch_code(client)).status_code == 200  # rahasia lama masih sah selama tumpang-tindih
    assert exchange(client, launch_code(client), secret="x" * 40).status_code == 401
    monkeypatch.setenv("SSO_CLIENT_SECRET_SUKAKETEMU_NEXT", "pendek")  # < 32 karakter diabaikan
    assert exchange(client, launch_code(client), secret="pendek").status_code == 401


# ----------------------------------------------------------------------------- Redis (fakeredis)
@pytest.fixture
def redis_env(monkeypatch):
    server = fakeredis.FakeServer()
    url = "redis://redis-test:6379/0"
    monkeypatch.setenv("REDIS_URL", url)
    store.use_client(url, fakeredis.FakeRedis(server=server, decode_responses=True))
    yield server, url


def test_redis_kode_sekali_pakai_dan_dibagi_antar_worker(redis_env):
    server, url = redis_env
    code = store.issue_code({"user": {"id": "u"}, "sid": "s", "service": "paas", "challenge": None}, 30)
    store.use_client(url, fakeredis.FakeRedis(server=server, decode_responses=True))  # "worker lain", server sama
    assert store.consume_code(code)["service"] == "paas"
    assert store.consume_code(code) is None


def test_redis_sesi_dicabut_di_satu_worker_mati_di_semua(redis_env, user):
    server, url = redis_env
    token = sign_token(user, 3600)
    from app.tokens import decode_session
    sid = decode_session(token)["sid"]
    store.use_client(url, fakeredis.FakeRedis(server=server, decode_responses=True))
    store.revoke_session(sid)
    assert decode_session(token) is None


def test_redis_rate_limit_global(redis_env):
    results = [security.rate_limit("k", 3, 60)[0] for _ in range(5)]
    assert results == [True, True, True, False, False]


def test_redis_mati_sesi_gagal_tertutup_dan_kode_ditolak(monkeypatch, user):
    import redis

    class Dead:
        def __getattr__(self, name):
            def boom(*a, **k):
                raise redis.ConnectionError("down")
            return boom

    url = "redis://dead:6379/0"
    monkeypatch.setenv("REDIS_URL", url)
    store.use_client(url, Dead())
    assert store.touch_session("apa-saja") is False
    assert store.consume_code("apa-saja") is None
    with pytest.raises(store.StoreUnavailable):
        store.issue_code({}, 30)
    assert security.rate_limit("k", 1, 60)[0] is True  # turun ke penghitung memori, tidak membuka tanpa batas
    assert security.rate_limit("k", 1, 60)[0] is False


def test_launch_503_bila_penyimpanan_mati(client, session_cookie, monkeypatch):
    client.cookies.update(session_cookie)

    def boom(*a, **k):
        raise store.StoreUnavailable("down")

    monkeypatch.setattr(store, "issue_code", boom)
    assert client.get("/api/sso/launch", params={"app": "paas"}).status_code == 503


# ----------------------------------------------------------------------------- masukan dari IdP
def test_nama_dibersihkan_dan_foto_hanya_dari_google():
    u = derive_user("a@student.uin-suka.ac.id", "Bud\u202ei\x00 " + "X" * 500, "https://lh3.googleusercontent.com/a/x")
    assert "\u202e" not in u["name"] and "\x00" not in u["name"] and len(u["name"]) <= 120
    assert u["picture_url"].startswith("https://lh3.googleusercontent.com/")
    assert "picture_url" not in derive_user("a@student.uin-suka.ac.id", "A", "https://evil.example/x.png")
    assert "picture_url" not in derive_user("a@student.uin-suka.ac.id", "A", "https://googleusercontent.com.evil.example/x")
    assert "picture_url" not in derive_user("a@student.uin-suka.ac.id", "A", "http://lh3.googleusercontent.com/x")
    assert derive_user("zam@student.uin-suka.ac.id", "\u202e\x00")["name"] == "zam"  # nama kosong => bagian lokal email


# ----------------------------------------------------------------------------- widget dari layanan tak tepercaya
async def _fetch(body: bytes | dict, status=200):
    def handler(request):
        content = body if isinstance(body, bytes) else json.dumps(body).encode()
        return httpx.Response(status, content=content, headers={"content-type": "application/json"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        return await widgets.fetch_widget(get_service("sukaketemu"), "tok", c)


def with_data(**over):
    return {"status": "success", "data": {**GOOD_WIDGET["data"], **over}}


@pytest.mark.anyio
async def test_widget_valid_lolos():
    assert (await _fetch(GOOD_WIDGET))["app_id"] == "sukaketemu"


@pytest.mark.anyio
@pytest.mark.parametrize("over", [
    {"action_url": "javascript:alert(1)"},
    {"action_url": "//evil.example/x"},
    {"action_url": "https://evil.example/"},
    {"action_url": "/campusfix/dashboard"},          # tautan ke layanan lain
    {"action_url": "/sukaketemu\\..\\x"},
    {"active_count": -1},
])
async def test_widget_menolak_tautan_atau_angka_berbahaya(over):
    assert await _fetch(with_data(**over)) is None


@pytest.mark.anyio
async def test_widget_menolak_teks_terlalu_panjang_dan_terlalu_banyak_item():
    item = GOOD_WIDGET["data"]["recent_items"][0]
    assert await _fetch(with_data(summary_title="x" * 500)) is None
    assert await _fetch(with_data(recent_items=[item] * 11)) is None


@pytest.mark.anyio
async def test_widget_menolak_respons_raksasa():
    valid_but_huge = json.dumps({**GOOD_WIDGET, "pad": "a" * (widgets.MAX_BODY_BYTES + 10)}).encode()
    assert await _fetch(GOOD_WIDGET) is not None  # kontrol: tanpa bantalan, payload yang sama lolos
    assert await _fetch(valid_but_huge) is None
    assert await _fetch(b"[1,2,3]") is None
    assert await _fetch(b"bukan json") is None


# ----------------------------------------------------------------------------- log audit
def test_log_audit_tanpa_data_pribadi(client, session_cookie, user, caplog):
    caplog.set_level(logging.INFO, logger="mysuka.audit")
    client.cookies.update(session_cookie)
    code = launch_code(client)
    exchange(client, code)
    exchange(client, code)  # kode dipakai ulang
    exchange(client, "x" * 30, secret="salah" * 10)
    client.post("/api/sso/logout", headers={"origin": "https://mysuka.test"})
    lines = [json.loads(r.message) for r in caplog.records if r.name == "mysuka.audit"]
    names = [l["event"] for l in lines]
    assert {"launch", "exchange_ok", "exchange_fail", "logout"} <= set(names)
    blob = "\n".join(r.message for r in caplog.records)
    for secret in (user["email"], user["name"], user["nim_nip"], code, secret_of("sukaketemu"), session_cookie["mysuka_session"]):
        assert secret not in blob
    assert all(set(l) <= {"event", "service", "reason", "user", "ip", "sid_hash", "count"} for l in lines)


def test_mask_ip():
    assert audit.mask_ip("203.0.113.77") == "203.0.113.0/24"
    assert audit.mask_ip("2001:db8:abcd:1234::1") == "2001:db8:abcd:1200::/56"
    assert audit.mask_ip("bukan-ip") == "-" and audit.mask_ip(None) == "-"


# ----------------------------------------------------------------------------- header API
def test_header_keamanan_api(client, monkeypatch):
    r = client.get("/healthz")
    assert r.headers["x-frame-options"] == "DENY" and "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert "geolocation=()" in r.headers["permissions-policy"] and "strict-transport-security" not in r.headers
    monkeypatch.setenv("ENV", "production")
    assert "max-age=63072000" in client.get("/healthz").headers["strict-transport-security"]
