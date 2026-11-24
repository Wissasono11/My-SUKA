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
    pem = e.get("SSO_PRIVATE_KEY_PEM")
    return Settings(
        env=e.get("ENV", "development"),
        base_url=base,
        issuer=e.get("SSO_ISSUER", base).rstrip("/"),
        key_id=e.get("SSO_KEY_ID", "mysuka-superapp-key-2026-v1"),
        private_pem=pem.replace("\\n", "\n") if pem else None,
        session_ttl=int(e.get("SESSION_TTL_SECONDS", 8 * 3600)),
        handoff_ttl=int(e.get("HANDOFF_TTL_SECONDS", 120)),
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
    )
