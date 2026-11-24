import asyncio
import os
import time
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from .config import get_settings
from .services import SERVICES, Service
from .tokens import sign_token

WIDGET_TIMEOUT_S = 1.5  # kontrak 4.3
CACHE_TTL_S = 45.0


class RecentItem(BaseModel):
    id: str
    title: str
    subtitle: str
    updated_at: str


class WidgetData(BaseModel):
    summary_title: str
    active_count: int
    count_label: str
    badge_status: str | None = None
    badge_label: str | None = None
    recent_items: list[RecentItem]
    action_url: str


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
            res = await client.get(
                f"{origin}{service.href}/api/widget/summary",
                headers={"authorization": f"Bearer {token}", "accept": "application/json"},
            )
        if res.status_code != 200:
            return None
        body = res.json()
        if body.get("status") != "success":
            return None
        data = WidgetData.model_validate(body.get("data"))
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
        *(fetch_widget_cached(s, user["id"], sign_token(user, ttl, service=s.id), client) for s in SERVICES if s.widget),
        return_exceptions=True,
    )
    return [r for r in results if isinstance(r, dict)]


def reset_widget_cache() -> None:
    _cache.clear()
