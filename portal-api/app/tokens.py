import time
import uuid
from typing import Any

import jwt

from .config import get_settings
from .identity import CampusUser, claims_for_service, session_user
from .keys import ALG, load_keys

AUDIENCE = "mysuka-microapps-ecosystem"


def sign_token(user: dict[str, Any], ttl_seconds: int, service: str | None = None) -> str:
    """service=None: token sesi portal (klaim penuh). service diisi: token serah-terima khusus layanan itu."""
    s = get_settings()
    private, _ = load_keys()
    now = int(time.time())
    claims = claims_for_service(user, service) if service else user
    payload = {
        "iss": s.issuer, "sub": claims["id"], "aud": AUDIENCE,
        "iat": now, "exp": now + ttl_seconds,
        "jti": uuid.uuid4().hex,  # layanan menolak jti yang sudah dipakai (anti-replay)
        "user": claims,
    }
    if service:
        payload["svc"] = service  # layanan menolak token yang bukan untuknya
    return jwt.encode(payload, private, algorithm=ALG, headers={"kid": s.key_id, "typ": "JWT"})


def verify_token(token: str) -> dict[str, Any] | None:
    s = get_settings()
    _, jwk = load_keys()
    try:
        public = jwt.PyJWK(jwk).key
        payload = jwt.decode(
            token, public, algorithms=[ALG], issuer=s.issuer, audience=AUDIENCE,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "jti"]},
        )
    except jwt.PyJWTError:
        return None
    user = payload.get("user")
    if not isinstance(user, dict) or not isinstance(user.get("id"), str) or not isinstance(user.get("email"), str):
        return None
    return user


def derive_user(email: str, name: str) -> dict[str, Any]:
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
    return session_user(cu)
