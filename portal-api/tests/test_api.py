from tests.conftest import decode_unverified


def test_healthz_dan_jwks_publik(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    r = client.get("/.well-known/jwks.json")
    key = r.json()["keys"][0]
    assert key["kty"] == "RSA" and key["alg"] == "RS256" and "d" not in key and "p" not in key
    assert "max-age=300" in r.headers["cache-control"]


def test_docs_aktif_di_mode_pengembangan(client):
    assert client.get("/api/docs").status_code == 200


def test_login_tanpa_google_dan_tanpa_dev_login_mengarah_ke_config(client):
    r = client.get("/api/sso/login")
    assert r.status_code == 307 and r.headers["location"] == "https://mysuka.test/login?error=config"


def test_login_dev_membuat_cookie_sesi(client, monkeypatch):
    monkeypatch.setenv("DEV_LOGIN", "1")
    r = client.get("/api/sso/login", params={"returnTo": "/layanan"})
    assert r.headers["location"] == "https://mysuka.test/layanan"
    assert "mysuka_session=" in r.headers["set-cookie"] and "HttpOnly" in r.headers["set-cookie"]


def test_login_dev_mati_di_produksi(client, monkeypatch):
    monkeypatch.setenv("DEV_LOGIN", "1")
    monkeypatch.setenv("ENV", "production")
    assert client.get("/api/sso/login").headers["location"].endswith("error=config")


def test_login_google_memakai_pkce_dan_state(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "sec")
    r = client.get("/api/sso/login", params={"returnTo": "https://evil.com"})
    loc = r.headers["location"]
    assert loc.startswith("https://accounts.google.com/") and "code_challenge_method=S256" in loc and "state=" in loc and "nonce=" in loc
    assert "mysuka_oidc=" in r.headers["set-cookie"] and "Path=/api/sso" in r.headers["set-cookie"]


def test_login_dibatasi_10_per_menit_per_ip(client):
    codes = [client.get("/api/sso/login", headers={"x-forwarded-for": "9.9.9.9"}).headers["location"] for _ in range(12)]
    assert codes[9].endswith("error=config") and codes[10].endswith("error=ratelimit")
    assert client.get("/api/sso/login", headers={"x-forwarded-for": "8.8.8.8"}).headers["location"].endswith("error=config")


def test_callback_tanpa_cookie_atau_state_salah_ditolak(client):
    assert client.get("/api/sso/callback", params={"code": "c", "state": "s"}).headers["location"].endswith("error=invalid")
    client.cookies.set("mysuka_oidc", '{"state":"a","nonce":"n","verifier":"v","returnTo":"/"}')
    assert client.get("/api/sso/callback", params={"code": "c", "state": "b"}).headers["location"].endswith("error=state")


def test_launch_tanpa_sesi_ke_login(client):
    r = client.get("/api/sso/launch", params={"app": "sukaketemu"})
    assert r.status_code == 307 and "/login?returnTo=%2Fapi%2Fsso%2Flaunch%3Fapp%3Dsukaketemu" in r.headers["location"]


def test_launch_layanan_tak_dikenal_404(client, session_cookie):
    client.cookies.update(session_cookie)
    assert client.get("/api/sso/launch", params={"app": "nope"}).status_code == 404


def test_launch_silent_login_token_pendek_dengan_jti(client, session_cookie):
    client.cookies.update(session_cookie)
    r = client.get("/api/sso/launch", params={"app": "sukaketemu"})
    assert r.status_code == 302 and r.headers["referrer-policy"] == "no-referrer" and r.headers["cache-control"] == "no-store"
    loc = r.headers["location"]
    assert loc.startswith("https://mysuka.test/sukaketemu/sso-callback?token=")
    payload, _ = decode_unverified(loc.split("token=")[1])
    assert payload["exp"] - payload["iat"] == 120 and len(payload["jti"]) == 32


def test_launch_dibatasi_30_per_menit_per_pengguna(client, session_cookie):
    client.cookies.update(session_cookie)
    codes = [client.get("/api/sso/launch", params={"app": "paas"}).status_code for _ in range(32)]
    assert codes[:30] == [302] * 30 and codes[30:] == [429, 429]


def test_logout_hanya_post_dengan_origin_sah(client):
    assert client.get("/api/sso/logout").status_code == 405
    assert client.post("/api/sso/logout").status_code == 403
    assert client.post("/api/sso/logout", headers={"origin": "https://evil.example"}).status_code == 403
    r = client.post("/api/sso/logout", headers={"origin": "https://mysuka.test"})
    assert r.status_code == 303 and r.headers["location"] == "https://mysuka.test/login"
    assert "Max-Age=0" in r.headers["set-cookie"]


def test_widget_summary_tanpa_sesi_401(client):
    assert client.get("/api/widget/summary").status_code == 401


def test_widget_summary_agregasi_siska_dikecualikan(client, session_cookie, calls):
    client.cookies.update(session_cookie)
    r = client.get("/api/widget/summary")
    body = r.json()
    assert r.status_code == 200 and body["status"] == "success"
    assert [w["app_id"] for w in body["data"]["widgets"]] == ["sukaketemu"]  # lain tak punya origin di env tes
    assert all(c.url.host != "siska.upstream" for c in calls)
    assert calls[0].headers["authorization"].startswith("Bearer ")
    assert r.headers["cache-control"] == "private, no-store"


def test_nama_cookie_mengikuti_env_dan_dapat_ditimpa(monkeypatch):
    from app.config import get_settings
    assert get_settings().session_cookie == "mysuka_session"
    monkeypatch.setenv("ENV", "production")
    assert get_settings().session_cookie == "__Host-mysuka_session"
    monkeypatch.setenv("SESSION_COOKIE_NAME", "x_session")
    assert get_settings().session_cookie == "x_session"


def test_logout_dev_menerima_loopback_dan_produksi_menolak(client, monkeypatch):
    lo = {"origin": "http://127.0.0.1:3000"}
    assert client.post("/api/sso/logout", headers=lo).status_code == 303
    monkeypatch.setenv("ENV", "production")
    r = client.post("/api/sso/logout", headers=lo)
    assert r.status_code == 403 and "APP_BASE_URL" in r.text
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://127.0.0.1:3000")
    assert client.post("/api/sso/logout", headers=lo).status_code == 303


def test_launch_terassc_berhasil(client, session_cookie):
    client.cookies.update(session_cookie)
    r = client.get("/api/sso/launch", params={"app": "terassc"})
    assert r.status_code == 302
    assert r.headers["location"].startswith("https://mysuka.test/terassc/sso-callback?token=")
