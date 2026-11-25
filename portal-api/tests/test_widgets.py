import asyncio

import httpx
import pytest

from app import widgets
from app.services import SERVICES, get_service
from tests.conftest import GOOD_WIDGET


def make(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_lima_layanan_sesuai_kontrak():
    assert [s.id for s in SERVICES] == ["sukaketemu", "campusfix", "siska", "archive", "paas", "terassc"]


def test_siska_tidak_pernah_ditarik():
    called = []

    async def go():
        async with make(lambda r: called.append(r) or httpx.Response(200, json=GOOD_WIDGET)) as c:
            return await widgets.fetch_widget(get_service("siska"), "t", c)

    assert asyncio.run(go()) is None and called == []


@pytest.mark.parametrize("resp", [
    httpx.Response(500), httpx.Response(200, json={"status": "success", "data": {"x": 1}}),
    httpx.Response(200, json={"status": "error"}), httpx.Response(200, text="bukan json"),
])
def test_kegagalan_dan_format_salah_menjadi_none(resp):
    async def go():
        async with make(lambda r: resp) as c:
            return await widgets.fetch_widget(get_service("sukaketemu"), "t", c)

    assert asyncio.run(go()) is None


def test_galat_jaringan_menjadi_none():
    def boom(request):
        raise httpx.ConnectError("down")

    async def go():
        async with make(boom) as c:
            return await widgets.fetch_widget(get_service("sukaketemu"), "t", c)

    assert asyncio.run(go()) is None


def test_respons_valid_diterima_dan_token_bearer_dikirim():
    seen = {}

    def ok(request):
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        return httpx.Response(200, json=GOOD_WIDGET)

    async def go():
        async with make(ok) as c:
            return await widgets.fetch_widget(get_service("sukaketemu"), "TOKEN", c)

    w = asyncio.run(go())
    assert w["app_id"] == "sukaketemu" and w["active_count"] == 2
    assert seen == {"auth": "Bearer TOKEN", "url": "https://sukaketemu.upstream/sukaketemu/api/widget/summary"}


def test_batas_waktu_1_5_detik_menahan_server_lambat(monkeypatch):
    monkeypatch.setattr(widgets, "WIDGET_TIMEOUT_S", 0.2)

    async def slow(request):
        await asyncio.sleep(5)
        return httpx.Response(200, json=GOOD_WIDGET)

    async def go():
        async with make(slow) as c:
            t0 = asyncio.get_running_loop().time()
            r = await widgets.fetch_widget(get_service("sukaketemu"), "t", c)
            return r, asyncio.get_running_loop().time() - t0

    r, dt = asyncio.run(go())
    assert r is None and dt < 1.0
