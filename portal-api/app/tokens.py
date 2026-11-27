import re
import time
import uuid
from typing import Any
from urllib.parse import urlparse

import jwt

from . import store
from .config import get_settings
from .identity import CampusUser, claims_for_service, service_sid, session_user
from .keys import ALG, load_keys

# Audience dibedakan per tujuan agar token tidak bisa dipakai silang (token confusion):
#   sesi portal  -> aud "mysuka-portal", typ "session" (hanya portal-api/portal-web yang menerima)
#   serah-terima -> aud = id layanan (mis. "siska"), typ "handoff" atau "widget"
SESSION_AUDIENCE = "mysuka-portal"
TYP_SESSION, TYP_HANDOFF, TYP_WIDGET = "session", "handoff", "widget"
BACKCHANNEL_EVENT = "http://schemas.openid.net/event/backchannel-logout"


def sign_token(
    user: dict[str, Any], ttl_seconds: int, service: str | None = None, purpose: str = TYP_HANDOFF, sid: str | None = None,
) -> str:
    """service=None: token sesi portal (klaim penuh, untuk cookie HttpOnly). service diisi: token pendek untuk
    layanan itu saja (aud=id layanan), berisi klaim minimal; `sid` portal ikut sebagai sid khusus layanan."""
    s = get_settings()
    private, _ = load_keys()
    now = int(time.time())
    payload: dict[str, Any] = {"iss": s.issuer, "iat": now, "exp": now + ttl_seconds, "jti": uuid.uuid4().hex}
    if service is None:
        payload.update(sub=user["id"], aud=SESSION_AUDIENCE, typ=TYP_SESSION, sid=sid or uuid.uuid4().hex, user=user)
        store.start_session(payload["sid"], payload["exp"])  # sesi sah hanya bila terdaftar di server (allowlist)
    else:
        claims = claims_for_service(user, service, purpose)
        payload.update(sub=claims["id"], aud=service, typ=purpose, svc=service, user=claims)
        if sid:
            payload["sid"] = service_sid(sid, service)
    return jwt.encode(payload, private, algorithm=ALG, headers={"kid": s.key_id, "typ": "JWT"})


def sign_logout_token(user: dict[str, Any], sid: str, service: str) -> str:
    """Logout token back-channel (OIDC Back-Channel Logout 1.0): dikirim server-ke-server ke layanan."""
    s = get_settings()
    private, _ = load_keys()
    now = int(time.time())
    claims = claims_for_service(user, service, TYP_WIDGET)
    payload = {
        "iss": s.issuer, "aud": service, "iat": now, "exp": now + 60, "jti": uuid.uuid4().hex,
        "sub": claims["id"], "sid": service_sid(sid, service), "events": {BACKCHANNEL_EVENT: {}},
    }
    return jwt.encode(payload, private, algorithm=ALG, headers={"kid": s.key_id, "typ": "logout+jwt"})


def decode_session(token: str) -> dict[str, Any] | None:
    """Verifikasi penuh token sesi portal: tanda tangan RS256, iss, aud, exp, typ, sid, dan belum dicabut."""
    s = get_settings()
    _, jwk = load_keys()
    try:
        public = jwt.PyJWK(jwk).key
        payload = jwt.decode(
            token, public, algorithms=[ALG], issuer=s.issuer, audience=SESSION_AUDIENCE,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "jti"]},
        )
    except jwt.PyJWTError:
        return None
    sid = payload.get("sid")
    if payload.get("typ") != TYP_SESSION or not isinstance(sid, str) or not sid:
        return None
    if not store.touch_session(sid):  # terdaftar, belum dicabut, belum lewat batas idle (sekaligus memperpanjang idle)
        return None
    user = payload.get("user")
    if not isinstance(user, dict) or not isinstance(user.get("id"), str) or not isinstance(user.get("email"), str):
        return None
    return payload


def verify_token(token: str) -> dict[str, Any] | None:
    """Pengguna dari token sesi yang sah, atau None."""
    payload = decode_session(token)
    return payload["user"] if payload else None


_CTRL = re.compile(r"[\x00-\x1f\x7f\u2028\u2029\u202a-\u202e\u2066-\u2069]")  # kontrol + pengarah teks (bidi)


def clean_name(name: str, fallback: str) -> str:
    """Nama dari IdP adalah masukan tak tepercaya: buang karakter kontrol/bidi dan batasi panjang (ukuran cookie)."""
    out = _CTRL.sub("", name or "").strip()[:120]
    return out or _CTRL.sub("", fallback)[:120]


def safe_picture(url: str | None) -> str | None:
    """Foto profil hanya dari host Google (cegah pelacak/konten pihak ketiga lewat klaim `picture`)."""
    if not url or len(url) > 512:
        return None
    u = urlparse(url)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or u.username or u.password or not (host == "googleusercontent.com" or host.endswith(".googleusercontent.com")):
        return None
    return url


def derive_user(email: str, name: str, picture_url: str | None = None) -> dict[str, Any]:
    """Adaptor sementara untuk login Google. campus_id = email sampai kampus menyediakan id permanen."""
    s = get_settings()
    name = clean_name(name, email.split("@")[0])
    local, _, domain = email.lower().partition("@")
    if email.lower() in s.admin_emails:
        role = "ADMIN"
    elif domain in s.student_domains:
        role = "MAHASISWA"
    else:
        role = "DOSEN"
    cu = CampusUser(
        campus_id=email.lower(), email=email, name=name, role=role,
        nim=local if role == "MAHASISWA" else None, nip=local if role != "MAHASISWA" else None,
    )
    user = session_user(cu)
    if safe_picture(picture_url):
        user["picture_url"] = picture_url
    return user
