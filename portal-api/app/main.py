import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from .config import get_settings, validate_startup
from .deps import current_user, http_client
from .identity import identity_secret
from .keys import load_jwks, load_keys
from .logging_utils import install as install_log_redaction
from . import store
from .routes_sso import router as sso_router
from .services import SERVICES
from .widgets import gather_widgets


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_keys()  # gagal cepat bila kunci produksi tidak valid
    identity_secret()  # gagal cepat bila IDENTITY_HMAC_SECRET kosong di produksi
    load_jwks()  # gagal cepat bila SSO_RETIRED_JWKS salah/memuat kunci privat
    store.ping()  # gagal cepat bila REDIS_URL diisi tetapi tidak terjangkau (jangan jalan setengah-aman)
    for warning in validate_startup(get_settings(), [sv.id for sv in SERVICES]):
        logging.getLogger("mysuka.config").warning(warning)
    app.state.http = httpx.AsyncClient(
        timeout=httpx.Timeout(5.0, connect=1.0), limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        follow_redirects=False,
    )
    yield
    await app.state.http.aclose()


install_log_redaction()  # query string (kode OIDC/state/token) tidak boleh tercatat di access log
_prod = get_settings().production
app = FastAPI(
    title="MySuka Portal API", lifespan=lifespan,
    docs_url=None if _prod else "/api/docs", redoc_url=None, openapi_url=None if _prod else "/api/openapi.json",
)
app.include_router(sso_router)


@app.middleware("http")
async def security_headers(request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # API tidak menyajikan HTML/skrip: kebijakan paling ketat. (Dokumentasi /api/docs hanya ada di dev dan butuh CDN.)
    if not request.url.path.startswith("/api/docs"):
        resp.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
    if get_settings().production:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/.well-known/jwks.json")
async def jwks():
    return JSONResponse(load_jwks(), headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=3600"})


@app.get("/api/widget/summary")
async def widget_summary(user: dict[str, Any] = Depends(current_user), client: httpx.AsyncClient = Depends(http_client)):
    """Agregator tipis (kontrak 4): hasil per layanan independen, yang gagal dibuang."""
    widgets = await gather_widgets(user, client)
    return JSONResponse({"status": "success", "data": {"widgets": widgets}}, headers={"Cache-Control": "private, no-store"})
