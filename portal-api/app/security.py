"""Rate limit, CSRF, dan validasi returnTo."""
import os
import re
import time
from urllib.parse import urlparse

from fastapi import Request

_buckets: dict[str, tuple[int, float]] = {}
MAX_KEYS = 10_000


def rate_limit(key: str, limit: int, window_s: float, now: float | None = None) -> tuple[bool, int]:
    """Fixed window di memori, per proses. Untuk batas global/multi-worker pakai Redis atau rate limit di edge."""
    now = time.monotonic() if now is None else now
    entry = _buckets.get(key)
    if entry is None or entry[1] <= now:
        if len(_buckets) >= MAX_KEYS:
            _prune(now)
        _buckets[key] = (1, now + window_s)
        return True, 0
    count, reset = entry[0] + 1, entry[1]
    _buckets[key] = (count, reset)
    if count <= limit:
        return True, 0
    return False, max(1, int(reset - now + 0.999))


def rate_limited(key: str, limit: int, now: float | None = None) -> bool:
    """Memeriksa tanpa menambah hitungan: True bila `key` sudah melewati `limit` dalam jendela berjalan."""
    now = time.monotonic() if now is None else now
    entry = _buckets.get(key)
    return entry is not None and entry[1] > now and entry[0] >= limit


def _prune(now: float) -> None:
    for k in [k for k, (_, r) in _buckets.items() if r <= now]:
        del _buckets[k]
    for k in list(_buckets):
        if len(_buckets) < MAX_KEYS * 0.9:
            break
        del _buckets[k]


def reset_rate_limits() -> None:
    _buckets.clear()


def client_ip(request: Request) -> str:
    """IP klien untuk rate limit. Di belakang proxy tepercaya (Caddy menimpa X-Forwarded-For dengan satu nilai) yang
    dipakai adalah entri TERAKHIR: entri di kiri dapat dipalsukan klien. TRUST_PROXY=0 => abaikan header (tanpa proxy)."""
    peer = request.client.host if request.client else "unknown"
    if os.environ.get("TRUST_PROXY", "1") == "0":
        return peer
    xff = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    return xff[-1] if xff else (request.headers.get("x-real-ip") or peer)


_LOOPBACK = {"localhost", "127.0.0.1", "[::1]", "::1"}


def is_same_origin(
    request: Request, base_url: str, extra: tuple[str, ...] | list[str] = (), allow_loopback: bool = False
) -> bool:
    """Origin harus sama dengan APP_BASE_URL, atau ada di ALLOWED_ORIGINS.
    allow_loopback (hanya pengembangan): terima localhost/127.0.0.1 di port mana pun, karena developer sering
    membuka 127.0.0.1 padahal APP_BASE_URL memakai localhost."""
    origin = request.headers.get("origin")
    if origin:
        u = urlparse(base_url)
        if origin == f"{u.scheme}://{u.netloc}" or origin in extra:
            return True
        o = urlparse(origin)
        return allow_loopback and o.scheme == "http" and (o.hostname or "") in _LOOPBACK
    return request.headers.get("sec-fetch-site") == "same-origin"


def safe_return_to(value: str | None, fallback: str = "/dashboard") -> str:
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value or re.search(r"[\x00-\x1f]", value):
        return fallback
    return value
