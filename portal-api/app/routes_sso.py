import json
import logging

import httpx
import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse, RedirectResponse

from . import google
from .config import Settings
from .deps import http_client, settings_dep
from .security import client_ip, is_same_origin, rate_limit, safe_return_to
from .services import get_service
from .tokens import derive_user, sign_token, verify_token

log = logging.getLogger("mysuka.sso")
router = APIRouter(prefix="/api/sso")
NO_STORE = {"Cache-Control": "no-store"}


def _set_session(resp: RedirectResponse, s: Settings, user: dict) -> None:
    resp.set_cookie(
        s.session_cookie, sign_token(user, s.session_ttl), max_age=s.session_ttl,
        httponly=True, secure=s.production, samesite="lax", path="/",
    )


def _redirect(url: str, status: int = 307) -> RedirectResponse:
    return RedirectResponse(url, status_code=status, headers=NO_STORE)


@router.get("/login")
async def login(request: Request, returnTo: str | None = None, s: Settings = Depends(settings_dep)):
    if not rate_limit(f"login:{client_ip(request)}", 10, 60)[0]:
        return _redirect(f"{s.base_url}/login?error=ratelimit")
    target = safe_return_to(returnTo)

    if not s.google_configured and not s.production and s.dev_login:  # hanya pengembangan lokal
        resp = _redirect(f"{s.base_url}{target}")
        user = {**derive_user("23106050059@student.uin-suka.ac.id", "Radinka Rafie"), "faculty": "SAINTEK", "department": "Informatika"}
        _set_session(resp, s, user)
        return resp
    if not s.google_configured:
        return _redirect(f"{s.base_url}/login?error=config")

    state, nonce, verifier = google.random_token(), google.random_token(), google.random_token(48)
    resp = _redirect(google.authorize_url(s, state, nonce, google.pkce_challenge(verifier)))
    resp.set_cookie(
        "mysuka_oidc", json.dumps({"state": state, "nonce": nonce, "verifier": verifier, "returnTo": target}),
        max_age=600, httponly=True, secure=s.production, samesite="lax", path="/api/sso",
    )
    return resp


@router.get("/callback")
async def callback(
    request: Request, code: str | None = None, state: str | None = None,
    s: Settings = Depends(settings_dep), client: httpx.AsyncClient = Depends(http_client),
):
    def fail(reason: str) -> RedirectResponse:
        r = _redirect(f"{s.base_url}/login?error={reason}")
        r.delete_cookie("mysuka_oidc", path="/api/sso")
        return r

    if not rate_limit(f"callback:{client_ip(request)}", 20, 60)[0]:
        return fail("ratelimit")
    raw = request.cookies.get("mysuka_oidc")
    if not raw or not code or not state:
        return fail("invalid")
    try:
        saved = json.loads(raw)
        saved_state, nonce, verifier, return_to = saved["state"], saved["nonce"], saved["verifier"], saved["returnTo"]
    except (ValueError, KeyError, TypeError):
        return fail("invalid")
    if saved_state != state:
        return fail("state")
    try:
        id_token = await google.exchange_code(s, client, code, verifier)
        claims = await run_in_threadpool(google.verify_id_token, s, id_token, nonce)
    except (google.LoginDenied, httpx.HTTPError, jwt.PyJWTError) as e:
        log.error("callback gagal: %s", type(e).__name__)  # tanpa token/kode di log
        return fail("denied")
    resp = _redirect(f"{s.base_url}{safe_return_to(return_to)}")
    _set_session(resp, s, derive_user(claims["email"], claims.get("name") or claims["email"]))
    resp.delete_cookie("mysuka_oidc", path="/api/sso")
    return resp


@router.get("/launch")
async def launch(app: str, request: Request, s: Settings = Depends(settings_dep)):
    """Silent login (kontrak 2.3): 302 ke /{app}/sso-callback?token=JWT pendek (berisi jti)."""
    service = get_service(app)
    if not service:
        return PlainTextResponse("Layanan tidak ditemukan", status_code=404)
    token = request.cookies.get(s.session_cookie)
    user = verify_token(token) if token else None
    if not user:
        from urllib.parse import quote
        return _redirect(f"{s.base_url}/login?returnTo={quote(f'/api/sso/launch?app={service.id}', safe='')}")
    ok, retry = rate_limit(f"launch:{user['id']}", 30, 60)
    if not ok:
        return PlainTextResponse("Terlalu banyak permintaan", status_code=429, headers={**NO_STORE, "Retry-After": str(retry)})
    handoff = sign_token(user, s.handoff_ttl, service=service.id)
    resp = RedirectResponse(f"{s.base_url}{service.href}/sso-callback?token={handoff}", status_code=302)
    resp.headers.update({**NO_STORE, "Referrer-Policy": "no-referrer"})
    return resp


@router.post("/logout")
async def logout(request: Request, s: Settings = Depends(settings_dep)):
    """Mengubah status: hanya POST + cek Origin (mencegah logout-CSRF)."""
    if not is_same_origin(request, s.base_url, s.allowed_origins, allow_loopback=not s.production):
        log.warning("logout ditolak: origin=%s diharapkan=%s", request.headers.get("origin"), s.base_url)
        return PlainTextResponse(
            "Forbidden: Origin tidak cocok dengan APP_BASE_URL. Buka portal lewat alamat yang sama dengan APP_BASE_URL.",
            status_code=403, headers=NO_STORE,
        )
    resp = _redirect(f"{s.base_url}/login", 303)
    resp.delete_cookie(s.session_cookie, path="/", secure=s.production, httponly=True, samesite="lax")
    return resp
