"""Kunci penandatangan RS256. Produksi wajib memakai PEM dari environment; dev memakai kunci sementara."""
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
