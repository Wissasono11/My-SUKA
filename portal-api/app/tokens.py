import time
import uuid
from typing import Any

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
    if payload.get("typ") != TYP_SESSION or not isinstance(sid, str) or not sid or store.is_revoked(sid):
        return None
    user = payload.get("user")
    if not isinstance(user, dict) or not isinstance(user.get("id"), str) or not isinstance(user.get("email"), str):
        return None
    return payload


def verify_token(token: str) -> dict[str, Any] | None:
    """Pengguna dari token sesi yang sah, atau None."""
    payload = decode_session(token)
    return payload["user"] if payload else None


def derive_user(email: str, name: str, picture_url: str | None = None) -> dict[str, Any]:
    """Adaptor sementara untuk login Google. campus_id = email sampai kampus menyediakan id permanen."""
    s = get_settings()
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
    if picture_url and picture_url.startswith("https://"):
        user["picture_url"] = picture_url
    return user
