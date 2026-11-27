"""Contoh FastAPI lengkap untuk satu layanan (alur: /sso-start -> portal -> /sso-callback -> sesi lokal).

Ini REFERENSI, bukan produk: ganti `SESSIONS` dengan penyimpanan sesi layanan Anda (Redis/DB). Yang tidak boleh diubah:
urutan pemeriksaan (exchange -> verify_handoff -> sesi baru), cookie host-only, dan penolakan tanpa pengecualian.
"""
from __future__ import annotations

import secrets

from urllib.parse import parse_qs

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

from mysuka_sso import SessionIndex, SsoConfig, SsoError, Verifier, exchange_code, new_pkce, safe_next, security_headers, session_cookie


def create_app(cfg: SsoConfig, *, verifier: Verifier | None = None, sensitive: bool = False, post=None) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None if cfg.production else "/openapi.json")
    verifier = verifier or Verifier(cfg)
    sessions: dict[str, dict] = {}           # id sesi lokal -> {"sub":..., "role":..., "portal_sid":...}
    index = SessionIndex()
    cookie_name, cookie_kw = session_cookie(cfg)
    pkce_cookie = ("__Host-sso_pkce" if cfg.production else "sso_pkce")
    base = f"/{cfg.service_id}"

    @app.middleware("http")
    async def headers(request: Request, call_next):
        resp = await call_next(request)
        for k, v in security_headers(sensitive=sensitive, hsts=cfg.production).items():
            resp.headers.setdefault(k, v)
        return resp

    def current(request: Request) -> dict:
        s = sessions.get(request.cookies.get(cookie_name, ""))
        if not s:
            raise HTTPException(401, "unauthenticated")
        return s

    @app.get(f"{base}/sso-start")
    async def sso_start():
        """PKCE: layanan membuat verifier sendiri dan menitipkan challenge-nya ke portal."""
        verifier_, challenge = new_pkce()
        r = RedirectResponse(f"{cfg.issuer}/api/sso/launch?app={cfg.service_id}&code_challenge={challenge}&code_challenge_method=S256", 302)
        r.set_cookie(pkce_cookie, verifier_, max_age=300, httponly=True, secure=cfg.production, samesite="lax", path="/")
        return r

    @app.get(f"{base}/sso-callback")
    async def sso_callback(request: Request, code: str | None = None):
        # Mode lama ?token= SENGAJA tidak didukung: token di URL = bocor lewat riwayat/log/Referer.
        if not code:
            return PlainTextResponse("Permintaan tidak valid", status_code=400, headers={"Cache-Control": "no-store"})
        try:
            raw = exchange_code(cfg, code, request.cookies.get(pkce_cookie), post=post)
            claims = verifier.verify_handoff(raw)
        except SsoError:
            return PlainTextResponse("Masuk gagal. Mulai lagi dari portal.", status_code=401, headers={"Cache-Control": "no-store"})
        local = secrets.token_urlsafe(32)  # SESI BARU setiap login (anti session fixation); jangan memakai ulang id lama
        sessions[local] = {"sub": claims.sub, "role": claims.role, "portal_sid": claims.sid}
        index.bind(local, claims.sid)
        r = RedirectResponse(safe_next(request.query_params.get("next"), f"{base}/"), 303, headers={"Cache-Control": "no-store"})
        r.set_cookie(cookie_name, local, **cookie_kw)
        r.delete_cookie(pkce_cookie, path="/")
        return r

    @app.post(f"{base}/api/backchannel-logout")
    async def backchannel_logout(request: Request):
        raw = await request.body()  # form-urlencoded `logout_token=<JWT>`; tanpa python-multipart, ukuran dibatasi
        values = parse_qs(raw[:8192].decode("ascii", "ignore")).get("logout_token", [])
        try:
            if len(raw) > 8192 or len(values) != 1:
                raise SsoError("permintaan tidak valid")
            claims = verifier.verify_logout(values[0])
        except SsoError:
            return JSONResponse({"error": "invalid_request"}, status_code=400, headers={"Cache-Control": "no-store"})
        index.end_by_portal_sid(claims.sid, lambda i: sessions.pop(i, None))
        return JSONResponse({}, headers={"Cache-Control": "no-store"})

    @app.get(f"{base}/api/widget/summary")
    async def widget(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(401, "unauthenticated")
        try:
            claims = verifier.verify_widget(authorization[7:].strip())
        except SsoError:
            raise HTTPException(401, "unauthenticated") from None
        # Identitas HANYA dari token (claims.sub). Abaikan ?user_id=... dari klien (anti-IDOR).
        return {"status": "success", "data": {
            "summary_title": "Status", "active_count": 0, "count_label": "Laporan Aktif", "recent_items": [],
            "action_url": f"{base}/dashboard"}}

    @app.get(f"{base}/me")
    async def me(request: Request):
        s = current(request)
        return {"id": s["sub"], "role": s["role"]}

    return app
