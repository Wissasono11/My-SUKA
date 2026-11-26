"""Konfigurasi dibaca dari environment setiap kali dipanggil (mudah diuji, tanpa cache global)."""
import os
from dataclasses import dataclass


def _csv(name: str, default: str) -> list[str]:
    return [v.strip().lower() for v in os.environ.get(name, default).split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    env: str
    base_url: str
    issuer: str
    key_id: str
    private_pem: str | None
    session_ttl: int
    handoff_ttl: int
    google_client_id: str | None
    google_client_secret: str | None
    google_hosted_domain: str | None
    allowed_domains: list[str]
    student_domains: list[str]
    admin_emails: list[str]
    dev_login: bool
    cookie_name: str | None
    identity_secret: str | None
    privacy_services: list[str]
    allowed_origins: list[str]
    code_ttl: int
    legacy_token_handoff: bool
    trust_proxy: bool

    @property
    def production(self) -> bool:
        return self.env == "production"

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def session_cookie(self) -> str:
        if self.cookie_name:
            return self.cookie_name
        return "__Host-mysuka_session" if self.production else "mysuka_session"


def get_settings() -> Settings:
    e = os.environ
    base = e.get("APP_BASE_URL", "http://localhost:3000").rstrip("/")
    pem = (e.get("SSO_PRIVATE_KEY_PEM") or "").strip() or None
    return Settings(
        env=e.get("ENV", "development"),
        base_url=base,
        issuer=e.get("SSO_ISSUER", base).rstrip("/"),
        key_id=e.get("SSO_KEY_ID", "mysuka-superapp-key-2026-v1"),
        private_pem=pem.replace("\\n", "\n") if pem else None,
        session_ttl=int(e.get("SESSION_TTL_SECONDS", 8 * 3600)),
        handoff_ttl=max(10, min(int(e.get("HANDOFF_TTL_SECONDS", 60)), 120)),  # token serah-terima: 10-120 dtk
        google_client_id=e.get("GOOGLE_CLIENT_ID") or None,
        google_client_secret=e.get("GOOGLE_CLIENT_SECRET") or None,
        google_hosted_domain=e.get("GOOGLE_HOSTED_DOMAIN") or None,
        allowed_domains=_csv("ALLOWED_EMAIL_DOMAINS", "student.uin-suka.ac.id,uin-suka.ac.id"),
        student_domains=_csv("STUDENT_EMAIL_DOMAINS", "student.uin-suka.ac.id"),
        admin_emails=_csv("ADMIN_EMAILS", ""),
        dev_login=e.get("DEV_LOGIN") == "1",
        cookie_name=e.get("SESSION_COOKIE_NAME") or None,
        identity_secret=e.get("IDENTITY_HMAC_SECRET") or None,
        privacy_services=_csv("PRIVACY_SERVICES", "siska"),
        allowed_origins=[o.rstrip("/") for o in _csv("ALLOWED_ORIGINS", "")],
        code_ttl=max(5, min(int(e.get("SSO_CODE_TTL_SECONDS", 30)), 60)),  # kode otorisasi sekali pakai: 5-60 dtk
        legacy_token_handoff=e.get("SSO_LEGACY_TOKEN_HANDOFF") == "1",
        trust_proxy=e.get("TRUST_PROXY", "1") != "0",
    )


def client_secret(service_id: str) -> str | None:
    """Rahasia client per layanan untuk back-channel (`POST /api/sso/exchange`). Env: SSO_CLIENT_SECRET_<ID>."""
    v = (os.environ.get(f"SSO_CLIENT_SECRET_{service_id.upper()}") or "").strip()
    return v if len(v) >= 32 else None  # < 32 karakter dianggap tidak dikonfigurasi


def public_origin(service_id: str) -> str:
    """Origin publik khusus layanan (isolasi Same-Origin, mis. https://siska.mysuka.portal.ac.id). Kosong = origin portal."""
    return (os.environ.get(f"{service_id.upper()}_PUBLIC_ORIGIN") or "").strip().rstrip("/")


def backchannel_logout_url(service_id: str) -> str:
    return (os.environ.get(f"{service_id.upper()}_BACKCHANNEL_LOGOUT_URL") or "").strip()


def validate_startup(s: Settings, service_ids: list[str]) -> list[str]:
    """Gagal cepat untuk salah-konfigurasi berbahaya di produksi; kembalikan daftar peringatan non-fatal."""
    from urllib.parse import urlparse
    warnings: list[str] = []
    for sid in service_ids:
        origin = public_origin(sid)
        if origin:
            u = urlparse(origin)
            if u.scheme not in ("https", "http") or not u.netloc or u.path or u.query or (s.production and u.scheme != "https"):
                raise RuntimeError(f"{sid.upper()}_PUBLIC_ORIGIN harus berupa origin (https://host) tanpa path")
        url = backchannel_logout_url(sid)
        if url and s.production and urlparse(url).scheme != "https":
            raise RuntimeError(f"{sid.upper()}_BACKCHANNEL_LOGOUT_URL wajib https di produksi")
        if s.production and not s.legacy_token_handoff and not client_secret(sid):
            warnings.append(f"SSO_CLIENT_SECRET_{sid.upper()} belum diisi (min. 32 karakter): launch ke layanan ini ditolak")
    if s.legacy_token_handoff and s.production:
        warnings.append("SSO_LEGACY_TOKEN_HANDOFF=1 di produksi: token masih dikirim lewat URL (tidak disarankan)")
    return warnings
