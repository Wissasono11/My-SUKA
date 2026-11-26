"""Kunci penandatangan RS256. Produksi wajib memakai PEM dari environment; dev memakai kunci sementara."""
import json
import logging
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from .config import get_settings

log = logging.getLogger("mysuka.keys")
ALG = "RS256"


@lru_cache(maxsize=1)
def _load(pem: str | None, production: bool, kid: str):
    if pem:
        try:
            private = serialization.load_pem_private_key(pem.encode(), password=None)
        except (ValueError, TypeError) as exc:
            if production:
                raise RuntimeError("SSO_PRIVATE_KEY_PEM tidak berisi PEM kunci privat RSA yang valid") from exc
            log.warning("SSO_PRIVATE_KEY_PEM tidak valid; memakai kunci sementara (hanya untuk pengembangan)")
            private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    elif production:
        raise RuntimeError("SSO_PRIVATE_KEY_PEM wajib di produksi")
    else:
        log.warning("memakai kunci sementara (hanya untuk pengembangan)")
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    jwk.update({"kid": kid, "alg": ALG, "use": "sig"})
    return private, jwk


def load_keys():
    s = get_settings()
    return _load(s.private_pem, s.production, s.key_id)


_PRIVATE_MEMBERS = {"d", "p", "q", "dp", "dq", "qi", "oth"}


def load_jwks() -> dict:
    """JWKS publik: kunci aktif + kunci lama (SSO_RETIRED_JWKS, JSON array JWK publik) selama masa tumpang-tindih rotasi,
    supaya layanan yang menyimpan JWKS di cache tetap dapat memverifikasi token yang baru ditandatangani kunci lama."""
    import os

    _, jwk = load_keys()
    keys = [jwk]
    raw = (os.environ.get("SSO_RETIRED_JWKS") or "").strip()
    if raw:
        try:
            retired = json.loads(raw)
            if not isinstance(retired, list):
                raise ValueError("harus array")
            for k in retired:
                if not isinstance(k, dict) or k.get("kty") != "RSA" or not k.get("kid") or k["kid"] == jwk["kid"]:
                    raise ValueError("JWK tidak valid atau kid sama dengan kunci aktif")
                if _PRIVATE_MEMBERS & k.keys():
                    raise ValueError("JWK memuat komponen kunci PRIVAT")
                keys.append({**k, "alg": ALG, "use": "sig"})
        except (ValueError, TypeError) as exc:
            raise RuntimeError(f"SSO_RETIRED_JWKS tidak valid: {exc}") from exc
    return {"keys": keys}
