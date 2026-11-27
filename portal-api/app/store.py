"""Penyimpanan jangka pendek: kode otorisasi sekali pakai dan sesi aktif.

Dua backend dengan antarmuka sama:
- Memori (default; satu proses): sesi dan kode hilang saat restart, jadi pengguna cukup login ulang.
- Redis (`REDIS_URL`): dipakai bersama oleh beberapa worker/replika dan bertahan saat portal-api restart.

Model sesi adalah ALLOWLIST: sebuah `sid` sah hanya bila terdaftar (dibuat saat login), belum melewati batas mutlak,
dan belum melewati batas tak-aktif (idle). Pencabutan = menghapus `sid`. Dibandingkan daftar-cabut (denylist), restart
atau kegagalan penyimpanan tidak pernah menghidupkan kembali sesi yang sudah dicabut: gagal => tutup.
"""
import hmac
import json
import logging
import secrets
import threading
import time
from typing import Any

from .config import get_settings

log = logging.getLogger("mysuka.store")
MAX_ENTRIES = 20_000


class StoreUnavailable(RuntimeError):
    """Penyimpanan tidak dapat dijangkau. Pemanggil harus gagal tertutup (503 / sesi dianggap tidak sah)."""


def _now() -> float:
    return time.time()


# --------------------------------------------------------------------------- memori
class MemoryBackend:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._codes: dict[str, tuple[float, dict[str, Any]]] = {}
        self._sessions: dict[str, tuple[float, float]] = {}  # sid -> (batas mutlak, batas idle)

    @staticmethod
    def _prune(table: dict, now: float, expiry_of) -> None:
        for k in [k for k, v in table.items() if expiry_of(v) <= now]:
            del table[k]
        while len(table) >= MAX_ENTRIES:  # batas keras: buang yang tertua (dict menjaga urutan sisip)
            del table[next(iter(table))]

    def issue_code(self, code: str, payload: dict[str, Any], ttl: int) -> None:
        now = _now()
        with self._lock:
            if len(self._codes) >= MAX_ENTRIES:
                self._prune(self._codes, now, lambda v: v[0])
            self._codes[code] = (now + ttl, payload)

    def consume_code(self, code: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._codes.pop(code, None)
        return entry[1] if entry is not None and entry[0] > _now() else None

    def start_session(self, sid: str, abs_exp: float, idle_ttl: int) -> None:
        now = _now()
        with self._lock:
            if len(self._sessions) >= MAX_ENTRIES:
                self._prune(self._sessions, now, lambda v: min(v[0], v[1]))
            self._sessions[sid] = (abs_exp, now + idle_ttl)

    def touch_session(self, sid: str, idle_ttl: int, slide: bool = True) -> bool:
        now = _now()
        with self._lock:
            entry = self._sessions.get(sid)
            if entry is None:
                return False
            abs_exp, idle_exp = entry
            if abs_exp <= now or idle_exp <= now:
                del self._sessions[sid]
                return False
            if slide:
                self._sessions[sid] = (abs_exp, now + idle_ttl)
            return True

    def revoke_session(self, sid: str) -> None:
        with self._lock:
            self._sessions.pop(sid, None)

    def clear(self) -> None:
        with self._lock:
            self._codes.clear()
            self._sessions.clear()


# --------------------------------------------------------------------------- Redis
class RedisBackend:
    def __init__(self, client) -> None:
        self.r = client

    def _guard(self, fn):
        import redis  # impor lambat: paket hanya wajib bila REDIS_URL diisi

        try:
            return fn()
        except redis.RedisError as exc:
            log.error("redis gagal: %s", type(exc).__name__)
            raise StoreUnavailable(type(exc).__name__) from exc

    def issue_code(self, code: str, payload: dict[str, Any], ttl: int) -> None:
        self._guard(lambda: self.r.set(f"code:{code}", json.dumps(payload), ex=ttl, nx=True))

    def consume_code(self, code: str) -> dict[str, Any] | None:
        raw = self._guard(lambda: self.r.getdel(f"code:{code}"))  # atomik: sekali pakai antarreplika
        return json.loads(raw) if raw else None

    def start_session(self, sid: str, abs_exp: float, idle_ttl: int) -> None:
        ttl = max(1, min(idle_ttl, int(abs_exp - _now())))
        self._guard(lambda: self.r.set(f"sess:{sid}", repr(abs_exp), ex=ttl))

    def touch_session(self, sid: str, idle_ttl: int, slide: bool = True) -> bool:
        raw = self._guard(lambda: self.r.get(f"sess:{sid}"))
        if raw is None:
            return False
        remaining = float(raw) - _now()
        if remaining <= 0:
            self._guard(lambda: self.r.delete(f"sess:{sid}"))
            return False
        if slide:
            self._guard(lambda: self.r.expire(f"sess:{sid}", max(1, min(idle_ttl, int(remaining)))))
        return True

    def revoke_session(self, sid: str) -> None:
        self._guard(lambda: self.r.delete(f"sess:{sid}"))

    def clear(self) -> None:
        self._guard(lambda: self.r.flushdb())


# --------------------------------------------------------------------------- pemilihan backend
_memory = MemoryBackend()
_redis_cache: dict[str, RedisBackend] = {}


def redis_client():
    """Klien Redis bersama (juga dipakai rate limit), atau None bila REDIS_URL kosong."""
    backend = _backend()
    return backend.r if isinstance(backend, RedisBackend) else None


def _backend():
    url = get_settings().redis_url
    if not url:
        return _memory
    be = _redis_cache.get(url)
    if be is None:
        import redis

        be = RedisBackend(redis.Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5, decode_responses=True))
        _redis_cache[url] = be
    return be


def use_client(url: str, client) -> None:
    """Untuk pengujian: pakai klien (mis. fakeredis) sebagai backend `url`."""
    _redis_cache[url] = RedisBackend(client)


def ping() -> None:
    """Gagal cepat saat start bila REDIS_URL diisi tetapi tidak dapat dijangkau."""
    be = _backend()
    if isinstance(be, RedisBackend):
        be._guard(lambda: be.r.ping())


# --------------------------------------------------------------------------- API publik (tidak berubah bagi pemanggil)
def issue_code(payload: dict[str, Any], ttl: int) -> str:
    code = secrets.token_urlsafe(32)  # 256 bit
    _backend().issue_code(code, payload, ttl)
    return code


def consume_code(code: str) -> dict[str, Any] | None:
    """Atomik dan sekali pakai: kode langsung dihapus, berhasil atau tidak. Penyimpanan rusak => None (tolak)."""
    try:
        return _backend().consume_code(code)
    except StoreUnavailable:
        return None


def start_session(sid: str, abs_exp: float) -> None:
    _backend().start_session(sid, abs_exp, get_settings().session_idle_ttl)


def touch_session(sid: str) -> bool:
    """True bila sesi sah; sekaligus memperpanjang batas idle. Penyimpanan rusak => False (gagal tertutup)."""
    try:
        return _backend().touch_session(sid, get_settings().session_idle_ttl, slide=True)
    except StoreUnavailable:
        return False


def session_alive(sid: str) -> bool:
    """Seperti touch_session tetapi tanpa memperpanjang idle (untuk pemeriksaan non-interaktif, mis. exchange)."""
    try:
        return _backend().touch_session(sid, get_settings().session_idle_ttl, slide=False)
    except StoreUnavailable:
        return False


def revoke_session(sid: str, expires_at: float | None = None) -> None:  # expires_at dipertahankan demi kompatibilitas
    try:
        _backend().revoke_session(sid)
    except StoreUnavailable:
        log.error("pencabutan sesi gagal: penyimpanan tidak tersedia")
        raise


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def reset() -> None:
    """Untuk pengujian: kosongkan memori dan lupakan backend Redis yang di-cache."""
    _memory.clear()
    for be in _redis_cache.values():
        try:
            be.clear()
        except StoreUnavailable:
            pass
    _redis_cache.clear()
