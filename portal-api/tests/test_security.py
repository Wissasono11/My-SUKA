from starlette.requests import Request

from app.security import client_ip, is_same_origin, rate_limit, safe_return_to


def req(headers: dict[str, str]):
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()], "client": ("5.5.5.5", 1)})


def test_rate_limit_batas_blokir_dan_pulih():
    for i in range(3):
        assert rate_limit("k", 3, 60, now=100 + i)[0]
    ok, retry = rate_limit("k", 3, 60, now=110)
    assert not ok and 49 <= retry <= 60
    assert rate_limit("k", 3, 60, now=161)[0]


def test_rate_limit_kunci_terpisah():
    rate_limit("a", 1, 60, now=0)
    assert not rate_limit("a", 1, 60, now=1)[0]
    assert rate_limit("b", 1, 60, now=1)[0]


def test_client_ip():
    assert client_ip(req({"x-forwarded-for": "1.2.3.4, 10.0.0.1"})) == "1.2.3.4"
    assert client_ip(req({})) == "5.5.5.5"


def test_csrf_origin():
    base = "https://mysuka.portal.ac.id"
    assert is_same_origin(req({"origin": base}), base)
    assert not is_same_origin(req({"origin": "https://evil.example"}), base)
    assert is_same_origin(req({"sec-fetch-site": "same-origin"}), base)
    assert not is_same_origin(req({"sec-fetch-site": "cross-site"}), base)
    assert not is_same_origin(req({}), base)


def test_csrf_origin_tambahan_dan_loopback_hanya_bila_diizinkan():
    base = "https://mysuka.portal.ac.id"
    assert is_same_origin(req({"origin": "https://alias.portal.ac.id"}), base, ["https://alias.portal.ac.id"])
    assert not is_same_origin(req({"origin": "http://127.0.0.1:3000"}), base)
    assert is_same_origin(req({"origin": "http://127.0.0.1:3000"}), base, allow_loopback=True)
    assert is_same_origin(req({"origin": "http://localhost:5173"}), base, allow_loopback=True)
    assert not is_same_origin(req({"origin": "https://127.0.0.1"}), base, allow_loopback=True)
    assert not is_same_origin(req({"origin": "http://evil.example"}), base, allow_loopback=True)
    assert not is_same_origin(req({"origin": "http://localhost.evil.example"}), base, allow_loopback=True)


def test_safe_return_to_menolak_open_redirect():
    for bad in ["https://evil.com", "//evil.com", "/\\evil.com", "javascript:alert(1)", "", None, "/a\nb"]:
        assert safe_return_to(bad) == "/dashboard"
    assert safe_return_to("/layanan") == "/layanan"
