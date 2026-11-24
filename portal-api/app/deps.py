from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request

from .config import Settings, get_settings
from .tokens import verify_token


def settings_dep() -> Settings:
    return get_settings()


def http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def current_user(request: Request, s: Settings = Depends(settings_dep)) -> dict[str, Any]:
    token = request.cookies.get(s.session_cookie)
    user = verify_token(token) if token else None
    if not user:
        raise HTTPException(401, "unauthenticated", headers={"Cache-Control": "no-store"})
    return user
