"""
auth.py — FastAPI dependency for JWT verification.

Verifies the Bearer token by calling Supabase's auth.getUser() endpoint.
This avoids needing the JWT secret locally — Supabase validates the token
server-side and returns the user if valid.

Falls back to local HS256 verification if SUPABASE_JWT_SECRET is set.

Usage in a route::

    from auth import get_current_user

    @app.post("/api/analyze")
    def analyze(request: AnalyzeRequest, current_user: str = Depends(get_current_user)):
        ...
"""

import os
import logging

import requests as http_requests
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def get_current_user(request: Request) -> str | None:
    """FastAPI dependency that verifies the Supabase JWT and returns the user_id.

    If no Authorization header is present, returns None (anonymous access).
    This allows the pipeline to work without Supabase auth configured.

    Raises:
        HTTPException(401): If a token IS provided but is invalid / expired.
    """
    auth_header: str | None = request.headers.get("Authorization")

    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authorization header must be 'Bearer <token>'",
        )

    token = parts[1]

    # Try local JWT verification first if secret is available
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    if jwt_secret:
        return _verify_local(token, jwt_secret)

    # Fall back to Supabase API verification
    return _verify_via_supabase(token)


def _verify_local(token: str, jwt_secret: str) -> str:
    """Verify JWT locally using HS256 and the Supabase JWT secret."""
    import jwt

    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    return user_id


def _verify_via_supabase(token: str) -> str:
    """Verify JWT by calling Supabase's auth.getUser() API."""
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url:
        logger.error("SUPABASE_URL is not set — cannot verify token")
        raise HTTPException(status_code=401, detail="Server authentication is not configured")

    if not service_key:
        logger.error("SUPABASE_SERVICE_ROLE_KEY is not set — cannot verify token")
        raise HTTPException(status_code=401, detail="Server authentication is not configured")

    try:
        resp = http_requests.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": service_key,
            },
            timeout=10,
        )
    except Exception as exc:
        logger.error("Failed to call Supabase auth API: %s", exc)
        raise HTTPException(status_code=401, detail="Authentication service unavailable")

    if resp.status_code != 200:
        detail = "Invalid or expired token"
        try:
            body = resp.json()
            if "msg" in body:
                detail = body["msg"]
            elif "message" in body:
                detail = body["message"]
        except Exception:
            pass
        raise HTTPException(status_code=401, detail=detail)

    user_data = resp.json()
    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Could not extract user ID from token")

    return user_id
