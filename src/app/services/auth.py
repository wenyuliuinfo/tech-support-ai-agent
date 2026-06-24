"""Auth service: JWT validation against Auth0 and account_id extraction."""

import logging
import time
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, Request
from jose import jwt
from jose.exceptions import JWTError

from config import get_settings

logger = logging.getLogger(__name__)

_jwks_cache: dict[str, Any] | None = None
_jwks_cache_ts: float = 0
_JWKS_TTL_SECONDS: int = 3600

_ACCOUNT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


async def _fetch_jwks(domain: str) -> dict:
    global _jwks_cache, _jwks_cache_ts
    now = time.time()
    if _jwks_cache and (now - _jwks_cache_ts) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    jwks_url = f"https://{domain}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_ts = now
        return _jwks_cache


def _sub_to_account_id(sub: str) -> uuid.UUID:
    try:
        return uuid.UUID(sub)
    except (ValueError, AttributeError):
        return uuid.uuid5(_ACCOUNT_NAMESPACE, sub)


async def _validate_jwt(token: str, settings: Any) -> dict:
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    jwks = await _fetch_jwks(settings.idp_domain)
    matching_key: dict | None = None
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            matching_key = key
            break

    if matching_key is None:
        raise HTTPException(status_code=401, detail="No matching JWK for token kid")

    return jwt.decode(
        token,
        matching_key,
        algorithms=["RS256"],
    )


async def _validate_opaque(token: str, domain: str) -> dict:
    userinfo_url = f"https://{domain}/userinfo"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid token")
        resp.raise_for_status()
        return resp.json()


async def get_account_id_from_request(request: Request) -> uuid.UUID:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]
    settings = get_settings()

    try:
        payload = await _validate_jwt(token, settings)
    except (JWTError, HTTPException):
        try:
            payload = await _validate_opaque(token, settings.idp_domain)
        except httpx.HTTPStatusError as e:
            logger.error(
                "Opaque token validation failed: status=%d body=%s",
                e.response.status_code,
                e.response.text[:500],
            )
            raise HTTPException(status_code=502, detail="Auth service error") from e
        except httpx.TimeoutException:
            logger.error("Opaque token validation timed out")
            raise HTTPException(status_code=504, detail="Auth service timeout") from None
        except httpx.HTTPError as e:
            logger.error("Opaque token validation network error: %s", type(e).__name__)
            raise HTTPException(status_code=502, detail="Auth service unavailable") from e
        except HTTPException:
            raise

    account_id_str = payload.get("sub")
    if not account_id_str:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    return _sub_to_account_id(account_id_str)
