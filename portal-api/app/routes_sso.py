import asyncio
import json
import logging
import re
from typing import Any

import httpx
import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field

from . import audit, google, store
from .config import Settings, backchannel_logout_url, client_secrets, pkce_required, public_origin
from .deps import current_user, http_client, settings_dep
from .security import client_ip, is_same_origin, rate_limit, rate_limited, safe_return_to
from .services import SERVICES, get_service
from .tokens import decode_session, derive_user, sign_logout_token, sign_token

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
        audit.event("rate_limited", reason="login", ip=audit.mask_ip(client_ip(request)))
        return _redirect(f"{s.base_url}/login?error=ratelimit")
    target = safe_return_to(returnTo)

    if not s.google_configured and not s.production and s.dev_login:  # hanya pengembangan lokal
        resp = _redirect(f"{s.base_url}{target}")
        user = {**derive_user("23106050017@student.uin-suka.ac.id", "Ahmad Zamroni"), "faculty": "SAINTEK", "department": "Informatika"}
        _set_session(resp, s, user)
        return resp
    if not s.google_configured:
        return _redirect(f"{s.base_url}/login?error=config")

    state, nonce, verifier = google.random_token(), google.random_token(), google.random_token(48)
    resp = _redirect(google.authorize_url(s, state, nonce, google.pkce_challenge(verifier)))
    resp.set_cookie(
        s.oidc_cookie, json.dumps({"state": state, "nonce": nonce, "verifier": verifier, "returnTo": target}),
        max_age=600, httponly=True, secure=s.production, samesite="lax", path=s.oidc_cookie_path,
    )
    return resp


@router.get("/callback")
async def callback(
    request: Request, code: str | None = None, state: str | None = None,
    s: Settings = Depends(settings_dep), client: httpx.AsyncClient = Depends(http_client),
):
    ip = audit.mask_ip(client_ip(request))

    def fail(reason: str) -> RedirectResponse:
        audit.event("login_denied", reason=reason, ip=ip)
        r = _redirect(f"{s.base_url}/login?error={reason}")
        r.delete_cookie(s.oidc_cookie, path=s.oidc_cookie_path, secure=s.production, httponly=True, samesite="lax")
        return r

    if not rate_limit(f"callback:{client_ip(request)}", 20, 60)[0]:
        return fail("ratelimit")
    raw = request.cookies.get(s.oidc_cookie)
    if not raw or not code or not state:
        return fail("invalid")
    try:
        saved = json.loads(raw)
        saved_state, nonce, verifier, return_to = saved["state"], saved["nonce"], saved["verifier"], saved["returnTo"]
    except (ValueError, KeyError, TypeError):
        return fail("invalid")
    if not store.constant_time_equals(str(saved_state), state):
        return fail("state")
    try:
        id_token = await google.exchange_code(s, client, code, verifier)
        claims = await run_in_threadpool(google.verify_id_token, s, id_token, nonce)
    except (google.LoginDenied, httpx.HTTPError, jwt.PyJWTError) as e:
        log.error("callback gagal: %s", type(e).__name__)  # tanpa token/kode di log
        return fail("denied")
    resp = _redirect(f"{s.base_url}{safe_return_to(return_to)}")
    user = derive_user(claims["email"], claims.get("name") or claims["email"], claims.get("picture"))
    try:
        _set_session(resp, s, user)
    except store.StoreUnavailable:
        return fail("unavailable")
    resp.delete_cookie(s.oidc_cookie, path=s.oidc_cookie_path, secure=s.production, httponly=True, samesite="lax")
    audit.event("login_success", user=user["id"], ip=ip)
    return resp


_CHALLENGE = re.compile(r"^[A-Za-z0-9_-]{43}$")  # BASE64URL(SHA-256) tanpa padding


@router.get("/launch")
async def launch(
    app: str, request: Request, code_challenge: str | None = None, code_challenge_method: str | None = None,
    s: Settings = Depends(settings_dep),
):
    """Silent login. Default: Authorization Code (302 ke /{app}/sso-callback?code=<kode sekali pakai, 30 dtk>); backend
    layanan menukarnya lewat POST /api/sso/exchange. JWT tidak pernah lewat URL. Mode lama (token di URL) hanya bila
    SSO_LEGACY_TOKEN_HANDOFF=1."""
    service = get_service(app)
    if not service:
        return PlainTextResponse("Layanan tidak ditemukan", status_code=404)
    token = request.cookies.get(s.session_cookie)
    session = decode_session(token) if token else None
    if not session:
        from urllib.parse import quote
        return _redirect(f"{s.base_url}/login?returnTo={quote(f'/api/sso/launch?app={service.id}', safe='')}")
    user, sid = session["user"], session["sid"]
    ok, retry = rate_limit(f"launch:{user['id']}", 30, 60)
    if not ok:
        return PlainTextResponse("Terlalu banyak permintaan", status_code=429, headers={**NO_STORE, "Retry-After": str(retry)})

    base = public_origin(service.id) or s.base_url
    headers = {**NO_STORE, "Referrer-Policy": "no-referrer"}
    if s.legacy_token_handoff:
        handoff = sign_token(user, s.handoff_ttl, service=service.id, sid=sid)
        return RedirectResponse(f"{base}{service.href}/sso-callback?token={handoff}", status_code=302, headers=headers)

    if not client_secrets(service.id):  # fail closed: tanpa rahasia client, layanan tak dapat menukar kode dengan aman
        log.error("launch ditolak: SSO_CLIENT_SECRET_%s belum dikonfigurasi", service.id.upper())
        audit.event("launch_denied", service=service.id, reason="no_client_secret")
        return PlainTextResponse("Layanan belum dikonfigurasi untuk SSO", status_code=503, headers=NO_STORE)
    challenge = None
    if code_challenge is not None:
        if code_challenge_method != "S256" or not _CHALLENGE.match(code_challenge):
            return PlainTextResponse("code_challenge tidak valid (wajib S256)", status_code=400, headers=NO_STORE)
        challenge = code_challenge
    elif pkce_required(s, service.id):  # layanan wajib PKCE: minta layanan memulai alurnya sendiri
        return RedirectResponse(f"{base}{service.href}/sso-start", status_code=302, headers=headers)
    try:
        code = store.issue_code({"user": user, "sid": sid, "service": service.id, "challenge": challenge}, s.code_ttl)
    except store.StoreUnavailable:
        return PlainTextResponse("Layanan sementara tidak tersedia", status_code=503, headers={**NO_STORE, "Retry-After": "5"})
    audit.event("launch", service=service.id, user=user["id"], reason="pkce" if challenge else "no_pkce")
    return RedirectResponse(f"{base}{service.href}/sso-callback?code={code}", status_code=302, headers=headers)


class ExchangeRequest(BaseModel):
    code: str = Field(min_length=20, max_length=200)
    client_id: str = Field(min_length=1, max_length=40)
    client_secret: str = Field(min_length=1, max_length=256)
    code_verifier: str | None = Field(default=None, min_length=43, max_length=128)


def _oauth_error(error: str, status: int) -> JSONResponse:
    return JSONResponse({"error": error}, status_code=status, headers={**NO_STORE, "Pragma": "no-cache"})


@router.post("/exchange")
async def exchange(body: ExchangeRequest, request: Request, s: Settings = Depends(settings_dep)):
    """Back-channel (server-ke-server): tukar kode sekali pakai dengan JWT serah-terima pendek (aud = layanan)."""
    ip = client_ip(request)
    if rate_limited(f"exchange-fail:{ip}", 10) or not rate_limit(f"exchange:{body.client_id}:{ip}", 120, 60)[0]:
        audit.event("rate_limited", reason="exchange", service=body.client_id[:40], ip=audit.mask_ip(ip))
        return _oauth_error("rate_limited", 429)
    service = get_service(body.client_id)
    secrets_ok = client_secrets(service.id) if service else []
    # Bandingkan ke SEMUA rahasia (utama + _NEXT) tanpa hubung-singkat agar waktu tidak membocorkan yang mana.
    matches = [store.constant_time_equals(body.client_secret, sec) for sec in secrets_ok]
    if not service or not any(matches):
        rate_limit(f"exchange-fail:{ip}", 10, 60)  # hitung hanya kegagalan: batasi tebakan rahasia
        audit.event("exchange_fail", reason="invalid_client", service=service.id if service else None, ip=audit.mask_ip(ip))
        return _oauth_error("invalid_client", 401)
    entry = store.consume_code(body.code)  # sekali pakai: terhapus walau verifikasi di bawah gagal
    if entry is None or entry["service"] != service.id:
        audit.event("exchange_fail", reason="invalid_grant", service=service.id, ip=audit.mask_ip(ip))
        return _oauth_error("invalid_grant", 400)
    if entry["challenge"] is None and pkce_required(s, service.id):
        audit.event("exchange_fail", reason="pkce_required", service=service.id, ip=audit.mask_ip(ip))
        return _oauth_error("invalid_grant", 400)
    if entry["challenge"] is not None:
        if not body.code_verifier or not store.constant_time_equals(google.pkce_challenge(body.code_verifier), entry["challenge"]):
            audit.event("exchange_fail", reason="pkce_mismatch", service=service.id, ip=audit.mask_ip(ip))
            return _oauth_error("invalid_grant", 400)
    if not store.session_alive(entry["sid"]):  # pengguna sudah logout / sesi idle selama kode beredar
        audit.event("exchange_fail", reason="session_ended", service=service.id, ip=audit.mask_ip(ip))
        return _oauth_error("invalid_grant", 400)
    audit.event("exchange_ok", service=service.id, user=entry["user"]["id"])
    token = sign_token(entry["user"], s.handoff_ttl, service=service.id, sid=entry["sid"])
    return JSONResponse(
        {"token": token, "token_type": "Bearer", "expires_in": s.handoff_ttl},
        headers={**NO_STORE, "Pragma": "no-cache"},
    )


@router.get("/session")
async def session_status(_: dict[str, Any] = Depends(current_user)):
    """Dipakai portal-web (internal) untuk memastikan sesi belum dicabut; verifikasi JWKS saja tidak mengetahuinya."""
    return JSONResponse({"active": True}, headers=NO_STORE)


async def _notify_backchannel(client: httpx.AsyncClient, user: dict[str, Any], sid: str) -> None:
    async def one(service_id: str, url: str) -> None:
        try:
            res = await client.post(url, data={"logout_token": sign_logout_token(user, sid, service_id)}, timeout=2.0)
            if res.status_code >= 400:  # layanan menolak: sesinya mungkin masih hidup di sana
                log.warning("back-channel logout ditolak layanan=%s status=%s", service_id, res.status_code)
                audit.event("backchannel_logout_failed", service=service_id, reason=f"http_{res.status_code}")
        except httpx.HTTPError as exc:
            log.warning("back-channel logout gagal: layanan=%s %s", service_id, type(exc).__name__)
            audit.event("backchannel_logout_failed", service=service_id, reason=type(exc).__name__)

    await asyncio.gather(*(one(sv.id, backchannel_logout_url(sv.id)) for sv in SERVICES if backchannel_logout_url(sv.id)))


@router.post("/logout")
async def logout(
    request: Request, background: BackgroundTasks, s: Settings = Depends(settings_dep),
    client: httpx.AsyncClient = Depends(http_client),
):
    """Mengubah status: hanya POST + cek Origin (mencegah logout-CSRF). Sesi dicabut di SERVER (bukan hanya cookie
    dihapus) dan layanan diberi tahu lewat back-channel logout."""
    if not is_same_origin(request, s.base_url, s.allowed_origins, allow_loopback=not s.production):
        log.warning("logout ditolak: origin=%s diharapkan=%s", request.headers.get("origin"), s.base_url)
        return PlainTextResponse(
            "Forbidden: Origin tidak cocok dengan APP_BASE_URL. Buka portal lewat alamat yang sama dengan APP_BASE_URL.",
            status_code=403, headers=NO_STORE,
        )
    token = request.cookies.get(s.session_cookie)
    session = decode_session(token) if token else None
    if session:
        try:
            store.revoke_session(session["sid"])
        except store.StoreUnavailable:
            audit.event("logout_revoke_failed", user=session["user"]["id"])  # cookie tetap dihapus; sesi mati oleh idle/exp
        else:
            audit.event("logout", user=session["user"]["id"])
        background.add_task(_notify_backchannel, client, session["user"], session["sid"])
    resp = _redirect(f"{s.base_url}/login", 303)
    resp.delete_cookie(s.session_cookie, path="/", secure=s.production, httponly=True, samesite="lax")
    resp.headers["Clear-Site-Data"] = '"cache", "storage"'  # bersihkan cache & storage origin portal (data layanan di bawahnya)
    return resp
