"""Penyimpanan jangka pendek: kode otorisasi sekali pakai dan daftar sesi yang dicabut.

Di memori, per proses (Dockerfile memakai satu worker). Untuk >1 worker/replika ganti isi modul ini dengan Redis
(`SET key val NX EX ttl` untuk kode, `GETDEL` untuk konsumsi atomik) tanpa mengubah pemanggil.
"""
import hmac
import secrets
import threading
import time
from typing import Any

_lock = threading.Lock()
_codes: dict[str, tuple[float, dict[str, Any]]] = {}
_revoked: dict[str, float] = {}
MAX_ENTRIES = 20_000


def _now() -> float:
    return time.time()


def _prune(table: dict, now: float, expiry_of) -> None:
    for k in [k for k, v in table.items() if expiry_of(v) <= now]:
        del table[k]
    while len(table) >= MAX_ENTRIES:  # batas keras: buang yang tertua (dict menjaga urutan sisip)
        del table[next(iter(table))]


def issue_code(payload: dict[str, Any], ttl: int) -> str:
    code = secrets.token_urlsafe(32)  # 256 bit
    now = _now()
    with _lock:
        if len(_codes) >= MAX_ENTRIES:
            _prune(_codes, now, lambda v: v[0])
        _codes[code] = (now + ttl, payload)
    return code


def consume_code(code: str) -> dict[str, Any] | None:
    """Atomik dan sekali pakai: kode langsung dihapus, berhasil atau tidak."""
    with _lock:
        entry = _codes.pop(code, None)
    if entry is None or entry[0] <= _now():
        return None
    return entry[1]


def revoke_session(sid: str, expires_at: float) -> None:
    now = _now()
    with _lock:
        if len(_revoked) >= MAX_ENTRIES:
            _prune(_revoked, now, lambda v: v)
        _revoked[sid] = expires_at


def is_revoked(sid: str) -> bool:
    with _lock:
        exp = _revoked.get(sid)
    return exp is not None and exp > _now()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def reset() -> None:
    with _lock:
        _codes.clear()
        _revoked.clear()
