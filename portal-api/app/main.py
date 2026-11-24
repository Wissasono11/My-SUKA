from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from .config import get_settings
from .deps import current_user, http_client
from .identity import identity_secret
from .keys import load_keys
from .routes_sso import router as sso_router
from .widgets import gather_widgets


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_keys()  # gagal cepat bila kunci produksi tidak valid
    identity_secret()  # gagal cepat bila IDENTITY_HMAC_SECRET kosong di produksi
    app.state.http = httpx.AsyncClient(
        timeout=httpx.Timeout(5.0, connect=1.0), limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        follow_redirects=False,
    )
    yield
    await app.state.http.aclose()


_prod = get_settings().production
app = FastAPI(
    title="MySuka Portal API", lifespan=lifespan,
    docs_url=None if _prod else "/api/docs", redoc_url=None, openapi_url=None if _prod else "/api/openapi.json",
)
app.include_router(sso_router)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/.well-known/jwks.json")
async def jwks():
    _, jwk = load_keys()
    return JSONResponse({"keys": [jwk]}, headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=3600"})


@app.get("/api/widget/summary")
async def widget_summary(user: dict[str, Any] = Depends(current_user), client: httpx.AsyncClient = Depends(http_client)):
    """Agregator tipis (kontrak 4): hasil per layanan independen, yang gagal dibuang."""
    widgets = await gather_widgets(user, client)
    return JSONResponse({"status": "success", "data": {"widgets": widgets}}, headers={"Cache-Control": "private, no-store"})
