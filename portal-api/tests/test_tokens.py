import jwt
import pytest

from app.keys import load_keys
from app.tokens import AUDIENCE, derive_user, sign_token, verify_token
from tests.conftest import decode_unverified


def test_token_rs256_sesuai_kontrak_dan_terverifikasi_jwks(user):
    token = sign_token(user, 60)
    payload, header = decode_unverified(token)
    assert header["alg"] == "RS256" and header["typ"] == "JWT" and header["kid"] == "mysuka-superapp-key-2026-v1"
    assert payload["aud"] == AUDIENCE and payload["sub"] == user["id"] and payload["sub"].startswith("usr_")
    assert "23106050059" not in payload["sub"], "sub tidak boleh membocorkan NIM/email"
    _, jwk = load_keys()
    assert "d" not in jwk, "JWKS tidak boleh memuat kunci privat"
    jwt.decode(token, jwt.PyJWK(jwk).key, algorithms=["RS256"], audience=AUDIENCE, issuer="https://mysuka.test")


def test_jti_unik_untuk_setiap_token(user):
    jtis = {decode_unverified(sign_token(user, 60))[0]["jti"] for _ in range(50)}
    assert len(jtis) == 50


def test_token_kedaluwarsa_atau_dirusak_ditolak(user):
    assert verify_token(sign_token(user, -10)) is None
    good = sign_token(user, 60)
    assert verify_token(good[:-4] + "AAAA") is None
    assert verify_token("bukan.token.sama-sekali") is None
    assert verify_token(good) is not None


def test_token_tanpa_jti_ditolak(user):
    from app.keys import load_keys as lk
    private, _ = lk()
    import time
    bad = jwt.encode({"iss": "https://mysuka.test", "sub": "x", "aud": AUDIENCE, "iat": int(time.time()), "exp": int(time.time()) + 60, "user": user}, private, algorithm="RS256")
    assert verify_token(bad) is None


def test_issuer_atau_audience_salah_ditolak(user, monkeypatch):
    token = sign_token(user, 60)
    monkeypatch.setenv("SSO_ISSUER", "https://lain.example")
    assert verify_token(token) is None


def test_derive_user_peran(monkeypatch):
    assert derive_user("a@student.uin-suka.ac.id", "A")["primary_role"] == "MAHASISWA"
    assert derive_user("b@uin-suka.ac.id", "B")["primary_role"] == "DOSEN"
    monkeypatch.setenv("ADMIN_EMAILS", "b@uin-suka.ac.id")
    assert derive_user("b@uin-suka.ac.id", "B")["primary_role"] == "ADMIN"


def test_produksi_tanpa_kunci_gagal_cepat(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    from app import keys
    keys._load.cache_clear()
    with pytest.raises(RuntimeError):
        keys.load_keys()
