"""Kit keamanan SSO My-SUKA untuk backend layanan (Python / FastAPI / Starlette / Flask).

Satu berkas, dua dependensi (`pyjwt[crypto]`, `httpx`). Semua pemeriksaan yang SERING terlewat tim layanan ada di sini
dan gagal tertutup: algoritma dikunci RS256, `iss`, `aud` (harus persis id layanan), `typ`, `svc`, `exp`, `iat`,
umur token maksimum, `jti` sekali pakai, serta aturan OIDC Back-Channel Logout. Salin berkas ini ke layanan Anda
(atau `pip install` dari repo ini) dan JANGAN menulis ulang verifikasinya sendiri.

Rahasia client (SSO_CLIENT_SECRET) hanya dibaca dari environment di server; modul ini tidak pernah mencatatnya.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient

__all__ = [
    "BACKCHANNEL_EVENT", "SsoConfig", "SsoError", "Claims", "MemoryReplayCache", "RedisReplayCache", "SessionIndex",
    "Verifier", "new_pkce", "exchange_code", "session_cookie", "security_headers", "safe_next",
]

BACKCHANNEL_EVENT = "http://schemas.openid.net/event/backchannel-logout"
MAX_TOKEN_LIFETIME = 120  # detik; portal menerbitkan 60 (handoff/widget) dan 60 (logout). Lebih panjang = ditolak.
LEEWAY = 5


class SsoError(Exception):
    """Token/kode/konfigurasi tidak sah. Pesan aman untuk log (tanpa token); jangan diteruskan ke pengguna."""


@dataclass(frozen=True)
class SsoConfig:
    service_id: str          # persis id layanan di portal, mis. "sukaketemu"
    issuer: str              # SSO_ISSUER, mis. https://mysuka.portal.ac.id
    jwks_url: str            # SSO_JWKS_URL
    exchange_url: str        # https://<portal>/api/sso/exchange
    client_secret: str       # SSO_CLIENT_SECRET (>= 32 karakter), hanya dari secret manager
    production: bool = True

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "SsoConfig":
        e = os.environ if env is None else env
        missing = [k for k in ("SSO_SERVICE_ID", "SSO_ISSUER", "SSO_JWKS_URL", "SSO_EXCHANGE_URL", "SSO_CLIENT_SECRET") if not e.get(k)]
        if missing:
            raise SsoError(f"environment belum lengkap: {', '.join(missing)}")
        cfg = cls(
            service_id=e["SSO_SERVICE_ID"], issuer=e["SSO_ISSUER"].rstrip("/"), jwks_url=e["SSO_JWKS_URL"],
            exchange_url=e["SSO_EXCHANGE_URL"], client_secret=e["SSO_CLIENT_SECRET"],
            production=e.get("ENV", "production").lower() not in ("development", "test"),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if len(self.client_secret) < 32:
            raise SsoError("SSO_CLIENT_SECRET minimal 32 karakter")
        for name, url in (("SSO_ISSUER", self.issuer), ("SSO_JWKS_URL", self.jwks_url), ("SSO_EXCHANGE_URL", self.exchange_url)):
            u = urlparse(url)
            if u.scheme not in ("https", "http") or not u.netloc:
                raise SsoError(f"{name} bukan URL yang valid")
            if self.production and u.scheme != "https" and u.hostname not in ("localhost", "127.0.0.1", "portal-api"):
                raise SsoError(f"{name} wajib https di produksi")


# ------------------------------------------------------------------------------------------ anti-replay (`jti`)
class ReplayCache(Protocol):
    def seen_before(self, key: str, ttl: int) -> bool:
        """Atomik: True bila `key` sudah pernah dicatat; bila belum, catat selama `ttl` detik dan kembalikan False."""


class MemoryReplayCache:
    """Per proses. Untuk >1 worker/replika pakai RedisReplayCache."""

    def __init__(self, max_entries: int = 50_000) -> None:
        self._lock, self._seen, self._max = threading.Lock(), {}, max_entries

    def seen_before(self, key: str, ttl: int) -> bool:
        now = time.time()
        with self._lock:
            if len(self._seen) >= self._max:
                for k in [k for k, exp in self._seen.items() if exp <= now]:
                    del self._seen[k]
                while len(self._seen) >= self._max:
                    del self._seen[next(iter(self._seen))]
            exp = self._seen.get(key)
            if exp is not None and exp > now:
                return True
            self._seen[key] = now + ttl
            return False


class RedisReplayCache:
    def __init__(self, client: Any, prefix: str = "sso:jti:") -> None:
        self.r, self.prefix = client, prefix

    def seen_before(self, key: str, ttl: int) -> bool:
        return self.r.set(self.prefix + key, "1", nx=True, ex=ttl) is None  # SET NX EX: None = sudah ada


# ------------------------------------------------------------------------------------------ indeks sesi untuk logout
class SessionIndex:
    """Memetakan `sid` portal -> sesi lokal layanan, agar back-channel logout dapat mengakhiri sesi yang benar.
    Ganti dengan tabel/Redis di produksi; antarmukanya sengaja kecil: bind() saat membuat sesi, end_by_portal_sid() saat logout."""

    def __init__(self) -> None:
        self._lock, self._by_portal = threading.Lock(), {}

    def bind(self, local_session_id: str, portal_sid: str) -> None:
        with self._lock:
            self._by_portal.setdefault(portal_sid, set()).add(local_session_id)

    def end_by_portal_sid(self, portal_sid: str, destroy: Callable[[str], None]) -> int:
        with self._lock:
            ids = self._by_portal.pop(portal_sid, set())
        for i in ids:
            destroy(i)
        return len(ids)


# ------------------------------------------------------------------------------------------ verifikasi token
@dataclass(frozen=True)
class Claims:
    sub: str            # id buram pengguna untuk layanan ini (usr_...)
    sid: str            # id sesi portal khusus layanan ini (sid_...)
    role: str | None
    user: dict[str, Any]
    jti: str
    raw: dict[str, Any]


class Verifier:
    def __init__(self, cfg: SsoConfig, replay: ReplayCache | None = None, jwks_client: Any | None = None) -> None:
        cfg.validate()
        self.cfg = cfg
        self.replay = replay or MemoryReplayCache()
        # Kunci HANYA dari JWKS_URL terkonfigurasi (PyJWKClient menolak token tanpa `kid` yang dikenal).
        self._jwks = jwks_client or PyJWKClient(cfg.jwks_url, cache_keys=True, lifespan=3600, timeout=3)

    def _decode(self, token: str, *, header_typ: str | None = None) -> dict[str, Any]:
        if not isinstance(token, str) or not token or len(token) > 8192:
            raise SsoError("token kosong atau terlalu panjang")
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":  # tolak none/HS*/ES*: kunci algoritma, jangan percaya header
                raise SsoError("alg bukan RS256")
            if header_typ is not None and str(header.get("typ", "")).lower() != header_typ:
                raise SsoError("typ header tidak sesuai")
            key = self._jwks.get_signing_key_from_jwt(token).key
            payload = jwt.decode(
                token, key, algorithms=["RS256"], issuer=self.cfg.issuer, audience=self.cfg.service_id, leeway=LEEWAY,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "jti"]},
            )
        except SsoError:
            raise
        except jwt.PyJWTError as exc:
            raise SsoError(f"token ditolak: {type(exc).__name__}") from exc
        except Exception as exc:  # noqa: BLE001 - jaringan JWKS dll.: gagal tertutup
            raise SsoError(f"verifikasi gagal: {type(exc).__name__}") from exc
        if payload["aud"] != self.cfg.service_id:  # PyJWT menerima daftar aud; kita wajib persis satu: layanan ini
            raise SsoError("aud bukan layanan ini")
        if not isinstance(payload["jti"], str) or not isinstance(payload["sub"], str):
            raise SsoError("jti/sub bukan string")
        if payload["exp"] - payload["iat"] > MAX_TOKEN_LIFETIME:
            raise SsoError("umur token melebihi batas")
        return payload

    def _claims(self, payload: dict[str, Any]) -> Claims:
        user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
        return Claims(sub=payload["sub"], sid=str(payload.get("sid", "")), role=user.get("primary_role"), user=user, jti=payload["jti"], raw=payload)

    def _once(self, payload: dict[str, Any], scope: str) -> None:
        ttl = max(1, int(payload["exp"] - time.time()) + LEEWAY + 1)
        if self.replay.seen_before(f"{scope}:{payload['jti']}", ttl):
            raise SsoError("jti sudah dipakai (replay)")

    def verify_handoff(self, token: str) -> Claims:
        """JWT hasil POST /api/sso/exchange. Sekali pakai. Setelah lolos, buat sesi lokal dan simpan `sid`."""
        p = self._decode(token)
        if p.get("typ") != "handoff" or p.get("svc") != self.cfg.service_id:
            raise SsoError("bukan token handoff untuk layanan ini")
        if not isinstance(p.get("sid"), str) or not p["sid"]:
            raise SsoError("sid tidak ada")
        self._once(p, "handoff")
        return self._claims(p)

    def verify_widget(self, token: str) -> Claims:
        """Bearer pada GET /<layanan>/api/widget/summary. Tidak sekali pakai (portal memakainya ulang dalam cache singkat)."""
        p = self._decode(token)
        if p.get("typ") != "widget" or p.get("svc") != self.cfg.service_id:
            raise SsoError("bukan token widget untuk layanan ini")
        return self._claims(p)

    def verify_logout(self, token: str) -> Claims:
        """`logout_token` pada POST /<layanan>/api/backchannel-logout (OIDC Back-Channel Logout 1.0 §2.6)."""
        p = self._decode(token, header_typ="logout+jwt")
        events = p.get("events")
        if not isinstance(events, dict) or BACKCHANNEL_EVENT not in events:
            raise SsoError("events tidak memuat backchannel-logout")
        if "nonce" in p:
            raise SsoError("logout token tidak boleh memuat nonce")
        if not isinstance(p.get("sid"), str) or not p["sid"]:
            raise SsoError("sid tidak ada")
        self._once(p, "logout")
        return self._claims(p)


# ------------------------------------------------------------------------------------------ exchange + PKCE
def new_pkce() -> tuple[str, str]:
    """(code_verifier, code_challenge S256). Simpan verifier di cookie HttpOnly pendek milik layanan, bukan di URL."""
    verifier = secrets.token_urlsafe(48)
    return verifier, base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


def exchange_code(cfg: SsoConfig, code: str, code_verifier: str | None = None, *, post: Callable[..., Any] | None = None) -> str:
    """Tukar `?code=` dengan JWT handoff (server-ke-server). Mengembalikan token MENTAH: lanjutkan ke Verifier.verify_handoff."""
    if not isinstance(code, str) or not (20 <= len(code) <= 200):
        raise SsoError("code tidak valid")
    import httpx

    body: dict[str, str] = {"code": code, "client_id": cfg.service_id, "client_secret": cfg.client_secret}
    if code_verifier:
        body["code_verifier"] = code_verifier
    try:
        res = (post or httpx.post)(cfg.exchange_url, json=body, timeout=3.0, follow_redirects=False)  # tanpa redirect: rahasia tak ikut ke host lain
    except Exception as exc:  # noqa: BLE001
        raise SsoError(f"exchange gagal: {type(exc).__name__}") from exc
    if res.status_code != 200:
        raise SsoError(f"exchange ditolak: {res.status_code}")
    data = res.json()
    token = data.get("token") if isinstance(data, dict) else None
    if not isinstance(token, str) or data.get("token_type") != "Bearer":
        raise SsoError("respons exchange tidak sah")
    return token


# ------------------------------------------------------------------------------------------ cookie, header, redirect
def session_cookie(cfg: SsoConfig, name: str = "session") -> tuple[str, dict[str, Any]]:
    """(nama, kwargs untuk `response.set_cookie`). Produksi: awalan __Host- (Secure, Path=/, tanpa Domain => host-only),
    HttpOnly, SameSite=Lax. Jangan pernah memberi `domain=`: cookie layanan tidak boleh terkirim ke subdomain lain."""
    prefixed = f"__Host-{name}" if cfg.production else name
    return prefixed, {"httponly": True, "secure": cfg.production, "samesite": "lax", "path": "/"}


def security_headers(*, sensitive: bool = False, hsts: bool = True) -> dict[str, str]:
    """Header dasar untuk SEMUA respons layanan. sensitive=True (mis. SISKA): tanpa cache dan referrer hanya same-origin."""
    h = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "same-origin" if sensitive else "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
    }
    if hsts:
        h["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    if sensitive:
        h["Cache-Control"] = "no-store"
    return h


def safe_next(value: str | None, fallback: str = "/") -> str:
    """Hanya path internal (cegah open redirect setelah login)."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value or any(ord(c) < 32 for c in value):
        return fallback
    return value
