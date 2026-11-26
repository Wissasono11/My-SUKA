"""Login Google (OIDC Authorization Code + PKCE)."""
import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from .config import Settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_JWKS = PyJWKClient("https://www.googleapis.com/oauth2/v3/certs", cache_keys=True, lifespan=3600)


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


def redirect_uri(s: Settings) -> str:
    return f"{s.base_url}/api/sso/callback"


def authorize_url(s: Settings, state: str, nonce: str, challenge: str) -> str:
    q = {
        "client_id": s.google_client_id, "redirect_uri": redirect_uri(s), "response_type": "code",
        "scope": "openid email profile", "state": state, "nonce": nonce,
        "code_challenge": challenge, "code_challenge_method": "S256", "prompt": "select_account",
    }
    if s.google_hosted_domain:
        q["hd"] = s.google_hosted_domain
    return f"{AUTH_URL}?{urlencode(q)}"


class LoginDenied(Exception):
    pass


def verify_id_token(s: Settings, id_token: str, nonce: str) -> dict:
    """Blocking (PyJWKClient): panggil lewat threadpool."""
    key = _GOOGLE_JWKS.get_signing_key_from_jwt(id_token).key
    claims = jwt.decode(
        id_token, key, algorithms=["RS256"], audience=s.google_client_id,
        issuer=["https://accounts.google.com", "accounts.google.com"],
        options={"require": ["exp", "iat", "iss", "aud", "sub", "email"]},
    )
    if claims.get("nonce") != nonce:
        raise LoginDenied("nonce tidak cocok")
    if claims.get("email_verified") is not True or not isinstance(claims.get("email"), str):
        raise LoginDenied("email belum terverifikasi")
    if claims["email"].split("@")[-1].lower() not in s.allowed_domains:
        raise LoginDenied("domain email tidak diizinkan")
    return claims


async def exchange_code(s: Settings, client: httpx.AsyncClient, code: str, verifier: str) -> str:
    res = await client.post(
        TOKEN_URL, timeout=5.0,
        data={
            "code": code, "client_id": s.google_client_id, "client_secret": s.google_client_secret,
            "redirect_uri": redirect_uri(s), "grant_type": "authorization_code", "code_verifier": verifier,
        },
    )
    res.raise_for_status()
    id_token = res.json().get("id_token")
    if not id_token:
        raise LoginDenied("id_token kosong")
    return id_token
