"""
Identitas pengguna lintas layanan.

Sumber kebenaran kredensial adalah database kampus; MySuka tidak menyimpan password. Penyedia login apa pun
(Google, SSO kampus, API, atau database) cukup menghasilkan `CampusUser`, lalu modul ini membentuk id yang
stabil dan buram (tanpa membocorkan email/NIM) serta id berbeda per layanan untuk layanan sensitif (SISKA).
"""
import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any

from .config import get_settings

log = logging.getLogger("mysuka.identity")
_DEV_SECRET = "dev-only-identity-secret-jangan-dipakai-di-produksi"


@dataclass(frozen=True)
class CampusUser:
    campus_id: str          # id PERMANEN dari sumber kampus (bukan email, karena email bisa berubah)
    email: str
    name: str
    role: str               # MAHASISWA | DOSEN | STAF | ADMIN
    nim: str | None = None
    nip: str | None = None
    faculty: str = ""
    department: str = ""


def identity_secret() -> bytes:
    s = get_settings()
    if s.identity_secret:
        return s.identity_secret.encode()
    if s.production:
        raise RuntimeError("IDENTITY_HMAC_SECRET wajib di produksi")
    log.warning("memakai IDENTITY_HMAC_SECRET sementara (hanya untuk pengembangan)")
    return _DEV_SECRET.encode()


def opaque_id(campus_id: str, scope: str = "global") -> str:
    """HMAC-SHA256: stabil untuk pengguna yang sama, tidak dapat dibalik, berbeda per `scope` (layanan)."""
    digest = hmac.new(identity_secret(), f"v1:{scope}:{campus_id}".encode(), hashlib.sha256).hexdigest()
    return f"usr_{digest[:32]}"


def session_user(cu: CampusUser) -> dict[str, Any]:
    """Isi sesi portal (cookie HttpOnly). Hanya dibaca portal; tidak pernah diteruskan ke layanan."""
    return {
        "id": opaque_id(cu.campus_id), "campus_id": cu.campus_id, "nim_nip": cu.nim or cu.nip or cu.campus_id,
        "email": cu.email, "name": cu.name, "primary_role": cu.role, "faculty": cu.faculty, "department": cu.department,
    }


def claims_for_service(user: dict[str, Any], service_id: str, purpose: str = "handoff") -> dict[str, Any]:
    """Klaim yang dikirim ke layanan tertentu (minimisasi data).

    - Layanan sensitif (PRIVACY_SERVICES, default SISKA): id sendiri + peran saja, tanpa email/nama/NIM.
    - purpose="widget": hanya id dan peran; ringkasan beranda tidak butuh email/nama/NIM.
    - Lainnya (handoff): profil lengkap untuk pembuatan profil just-in-time.
    """
    if service_id in get_settings().privacy_services:
        return {"id": opaque_id(user["campus_id"], scope=service_id), "primary_role": user["primary_role"]}
    if purpose == "widget":
        return {"id": user["id"], "primary_role": user["primary_role"]}
    return {k: user[k] for k in ("id", "nim_nip", "email", "name", "primary_role", "faculty", "department")}


def service_sid(sid: str, service_id: str) -> str:
    """sid per layanan: layanan sensitif tidak boleh dapat dikorelasikan dengan layanan lain lewat sid yang sama."""
    digest = hmac.new(identity_secret(), f"v1:sid:{service_id}:{sid}".encode(), hashlib.sha256).hexdigest()
    return f"sid_{digest[:32]}"
