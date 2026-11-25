import pytest

from app.identity import CampusUser, claims_for_service, identity_secret, opaque_id, session_user
from app.tokens import derive_user, sign_token
from tests.conftest import decode_unverified


def test_opaque_id_stabil_buram_dan_berbeda_per_lingkup(monkeypatch):
    monkeypatch.setenv("IDENTITY_HMAC_SECRET", "rahasia-uji")
    a = opaque_id("23106050059")
    assert a == opaque_id("23106050059") and a.startswith("usr_") and len(a) == 36
    assert "23106050059" not in a
    assert a != opaque_id("23106050059", scope="siska")
    assert a != opaque_id("23106050060")
    monkeypatch.setenv("IDENTITY_HMAC_SECRET", "rahasia-lain")
    assert a != opaque_id("23106050059"), "tanpa rahasia yang sama, id tidak bisa direproduksi"


def test_produksi_tanpa_identity_secret_gagal_cepat(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    with pytest.raises(RuntimeError):
        identity_secret()


def test_session_user_memuat_campus_id_internal_dan_id_buram():
    cu = CampusUser(campus_id="U-77", email="a@student.uin-suka.ac.id", name="A", role="MAHASISWA", nim="23106050017")
    u = session_user(cu)
    assert u["campus_id"] == "U-77" and u["id"].startswith("usr_") and u["nim_nip"] == "23106050017"


def test_layanan_biasa_menerima_klaim_penuh_siska_minimal():
    u = derive_user("23106050017@student.uin-suka.ac.id", "Ahmad Zamroni")
    full = claims_for_service(u, "sukaketemu")
    assert full["email"] == u["email"] and full["id"] == u["id"] and "campus_id" not in full
    minimal = claims_for_service(u, "siska")
    assert set(minimal) == {"id", "primary_role"}
    assert minimal["id"] != u["id"] and minimal["id"] == opaque_id(u["campus_id"], scope="siska")


def test_privacy_services_dapat_dikonfigurasi(monkeypatch):
    u = derive_user("a@uin-suka.ac.id", "A")
    monkeypatch.setenv("PRIVACY_SERVICES", "siska,archive")
    assert set(claims_for_service(u, "archive")) == {"id", "primary_role"}
    monkeypatch.setenv("PRIVACY_SERVICES", "")
    assert "email" in claims_for_service(u, "siska")


def test_token_serah_terima_siska_tidak_memuat_data_pribadi_dan_terikat_layanan(user):
    payload, _ = decode_unverified(sign_token(user, 120, service="siska"))
    assert payload["svc"] == "siska" and payload["sub"] == payload["user"]["id"]
    blob = str(payload)
    for secret in (user["email"], user["name"], "23106050059"):
        assert secret not in blob
    other, _ = decode_unverified(sign_token(user, 120, service="paas"))
    assert other["user"]["email"] == user["email"] and other["svc"] == "paas"
    assert other["sub"] != payload["sub"]


def test_launch_siska_via_api_memakai_id_khusus(client, session_cookie, user):
    client.cookies.update(session_cookie)
    r = client.get("/api/sso/launch", params={"app": "siska"})
    payload, _ = decode_unverified(r.headers["location"].split("token=")[1])
    assert payload["svc"] == "siska" and set(payload["user"]) == {"id", "primary_role"}
    assert payload["sub"] == opaque_id(user["campus_id"], scope="siska")
