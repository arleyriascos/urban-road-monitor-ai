"""Protection of POST /routes with the token shared by the backend and this service.

The backend sends "Authorization: Bearer <INTERNAL_TOKEN>":

- Without INTERNAL_TOKEN configured the endpoint does not exist: the answer is the same
  404 as any unknown route.
- A missing or wrong token gets one 401 answer, with the same message in every case.
- Both tokens are compared through their SHA-256 hashes with hmac.compare_digest, so the
  response time reveals nothing about the right value or its length.
- The token is never logged or sent back.
"""

import hashlib
import hmac
import re

from fastapi import Request

from app.config import Settings
from app.errors import ApiError, route_not_found

_BEARER = re.compile(r"^Bearer\s+(.+)$", re.IGNORECASE)


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def require_internal_token(request: Request) -> None:
    """FastAPI dependency: let the request through only with the right token."""
    settings: Settings = request.app.state.settings
    if settings.internal_token is None:
        raise route_not_found(request)

    match = _BEARER.match(request.headers.get("authorization", ""))
    received = match.group(1).strip() if match else ""
    expected = settings.internal_token.get_secret_value()
    if not match or not hmac.compare_digest(_digest(received), _digest(expected)):
        raise ApiError(
            401,
            "UNAUTHORIZED",
            "A valid internal token is required",
            headers={"WWW-Authenticate": 'Bearer realm="internal"', "Cache-Control": "no-store"},
        )
