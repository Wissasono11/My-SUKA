import asyncio
import json
import os
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from .config import get_settings
from .security import safe_return_to
from .services import SERVICES, Service
from .tokens import TYP_WIDGET, sign_token

WIDGET_TIMEOUT_S = 1.5  # kontrak 4.3
CACHE_TTL_S = 45.0
MAX_BODY_BYTES = 32 * 1024  # layanan yang dibobol/salah tidak boleh membuat portal menampung respons raksasa


class RecentItem(BaseModel):
    id: str = Field(max_length=64)
    title: str = Field(max_length=120)
    subtitle: str = Field(max_length=200)
    updated_at: str = Field(max_length=40)


class WidgetData(BaseModel):
    summary_title: str = Field(max_length=80)
    active_count: int = Field(ge=0, le=10_000_000)
    count_label: str = Field(max_length=60)
    badge_status: str | None = Field(default=None, max_length=40)
    badge_label: str | None = Field(default=None, max_length=60)
    recent_items: list[RecentItem] = Field(max_length=10)
    action_url: str = Field(max_length=300)

    @field_validator("action_url")
    @classmethod
    def _relative_path_only(cls, v: str) -> str:
        # Hanya path internal: tolak javascript:, data:, //host, dan backslash (open redirect / XSS lewat tautan).
        if safe_return_to(v, fallback="") != v:
            raise ValueError("action_url harus path internal")
        return v


def origin_of(service: Service) -> str:
    return os.environ.get(service.origin_env, "").rstrip("/")


async def fetch_widget(service: Service, token: str, client: httpx.AsyncClient) -> dict[str, Any] | None:
    """Gagal, lambat, atau format salah => None (widget disembunyikan, halaman tetap utuh)."""
    if not service.widget:
        return None  # SISKA tidak pernah ditarik
    origin = origin_of(service)
    if not origin:
        return None
    try:
        async with asyncio.timeout(WIDGET_TIMEOUT_S):  # batas keras, termasuk saat membaca body
            async with client.stream(
                "GET", f"{origin}{service.href}/api/widget/summary",
                headers={"authorization": f"Bearer {token}", "accept": "application/json"},
            ) as res:
                if res.status_code != 200:
                    return None
                chunks, size = [], 0
                async for chunk in res.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_BODY_BYTES:
                        return None  # terlalu besar: buang
                    chunks.append(chunk)
        body = json.loads(b"".join(chunks))
        if not isinstance(body, dict) or body.get("status") != "success":
            return None
        data = WidgetData.model_validate(body.get("data"))
        if not data.action_url.startswith(f"{service.href}/") and data.action_url != service.href:
            return None  # tautan aksi harus tetap di dalam layanan itu sendiri
        return {"app_id": service.id, **data.model_dump(exclude_none=True)}
    except (TimeoutError, httpx.HTTPError, ValueError, ValidationError):
        return None  # tanpa log isi respons/token


_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}


async def fetch_widget_cached(service: Service, user_id: str, token: str, client: httpx.AsyncClient):
    key = f"{service.id}:{user_id}"
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
        return hit[1]
    widget = await fetch_widget(service, token, client)
    if len(_cache) > 500:
        _cache.pop(next(iter(_cache)))
    _cache[key] = (time.monotonic(), widget)
    return widget


async def gather_widgets(user: dict[str, Any], client: httpx.AsyncClient) -> list[dict[str, Any]]:
    ttl = get_settings().handoff_ttl
    results = await asyncio.gather(
        *(fetch_widget_cached(s, user["id"], sign_token(user, ttl, service=s.id, purpose=TYP_WIDGET), client) for s in SERVICES if s.widget),
        return_exceptions=True,
    )
    return [r for r in results if isinstance(r, dict)]


def reset_widget_cache() -> None:
    _cache.clear()
