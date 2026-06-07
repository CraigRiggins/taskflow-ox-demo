"""
Authentication routes.

Handles login and token issuance. Token storage is in-memory —
a proper implementation would use Redis or a signed JWT.
"""

import secrets
import time
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional

from app.models.user import LoginRequest, TokenResponse
from app.services import user_service
from app.db import queries

router = APIRouter()

# in-memory token store: token → {user_id, created_at, expires_at}
# not suitable for multi-process deployments
_tokens: dict[str, dict] = {}

TOKEN_TTL_SECONDS = 86400  # 24 hours


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Authenticates a user and returns an access token."""
    user = user_service.authenticate(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_urlsafe(32)
    now   = int(time.time())
    _tokens[token] = {
        "user_id":    user["id"],
        "created_at": now,
        "expires_at": now + TOKEN_TTL_SECONDS,
    }

    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        role=user["role"],
    )


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    """Invalidates the current token."""
    token = _extract_token(authorization)
    if token and token in _tokens:
        del _tokens[token]
    return {"status": "logged out"}


@router.get("/me")
def get_me(authorization: Optional[str] = Header(None)):
    """Returns the currently authenticated user."""
    user = require_auth(authorization)
    return {k: v for k, v in user.items() if k != "password"}


def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency — extracts and validates the bearer token.
    Raises 401 if missing or expired.

    This is called by every protected route and is a boundary function
    — changes here affect the entire API surface.
    """
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Authorization header required")

    entry = _tokens.get(token)
    if not entry:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if int(time.time()) > entry["expires_at"]:
        del _tokens[token]
        raise HTTPException(status_code=401, detail="Token expired")

    user = queries.get_user_by_id(entry["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_admin(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency — requires admin role."""
    user = require_auth(authorization)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    """Parses 'Bearer <token>' from the Authorization header."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
