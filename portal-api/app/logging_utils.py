"""Redaksi log: query string (kode OIDC, state, token) tidak boleh masuk access log."""
import logging
import re

_QUERY = re.compile(r"\?[^\s]*")


class RedactQueryFilter(logging.Filter):
    """Untuk logger `uvicorn.access`, yang args-nya (client, method, path+query, http_version, status)."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str) and "?" in args[2]:
            record.args = (*args[:2], _QUERY.sub("?[redacted]", args[2], count=1), *args[3:])
        return True


def install() -> None:
    log = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactQueryFilter) for f in log.filters):
        log.addFilter(RedactQueryFilter())
