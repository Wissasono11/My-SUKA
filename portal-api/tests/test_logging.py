import logging

from app.logging_utils import RedactQueryFilter


def test_query_string_disamarkan_di_access_log():
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                            ("1.2.3.4:5", "GET", "/api/sso/callback?code=SECRET&state=S2", "1.1", 307), None)
    assert RedactQueryFilter().filter(rec)
    out = rec.getMessage()
    assert "SECRET" not in out and "S2" not in out and "/api/sso/callback?[redacted]" in out


def test_tanpa_query_tidak_berubah():
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d', ("c", "GET", "/healthz", "1.1", 200), None)
    RedactQueryFilter().filter(rec)
    assert "/healthz" in rec.getMessage()
