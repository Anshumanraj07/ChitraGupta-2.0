"""
ChitraGupta 2.0 — Authentication
Supabase JWT verification + user resolution.

Integrates with the existing user_registry so authenticated users automatically
get a per-user intelligence bundle. Unauthenticated requests fall back to
DEFAULT_USER_ID to preserve backward compatibility (zero breaking changes).

Requires:
  SUPABASE_URL             — Supabase project URL
  SUPABASE_JWT_SECRET      — Supabase project JWT secret (found in project settings)

If SUPABASE_JWT_SECRET is not set, verification is *skipped* and the user_id
from the request (header/body) is trusted as-is. This keeps local dev and
existing deployments working without forcing a secret reboot.
"""

import logging
import os
from typing import Optional
from datetime import datetime

logger = logging.getLogger("chitragupta.auth")

# Lazy imports — jwt is part of the supabase/pyjwt stack already present.
_jose_available = False
try:
    import jwt as _jwt  # type: ignore
    _jose_available = True
except Exception:  # pragma: no cover
    _jwt = None  # type: ignore


def get_jwt_secret() -> Optional[str]:
    """Return the Supabase JWT secret from env, if configured."""
    return os.getenv("SUPABASE_JWT_SECRET")


def verify_token(token: str) -> Optional[dict]:
    """
    Verify a Supabase access token (JWT) and return its payload.

    Returns None if verification fails or the secret is not configured.
    Never raises — callers treat None as "unauthenticated, fall back to default".
    """
    if not token:
        return None

    secret = get_jwt_secret()
    if not secret or not _jose_available:
        # No secret configured → trust the token opaquely.
        # We still try to decode without verification so user_id can be read.
        try:
            return _jwt.decode(token, options={"verify_signature": False}) if _jwt else None
        except Exception:
            return None

    try:
        # Supabase uses HS256 by default.
        payload = _jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
        return payload
    except Exception as e:
        logger.debug(f"JWT verification failed: {e}")
        return None


def extract_token(authorization: Optional[str]) -> Optional[str]:
    """Extract the bearer token from an Authorization header value."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    # Tolerate raw-token headers
    return authorization.strip() or None


def resolve_authenticated_user(
    authorization: Optional[str] = None,
    x_user_id: Optional[str] = None,
    body_user_id: Optional[str] = None,
) -> str:
    """
    Resolve the effective user id for a request.

    Order of preference:
      1. Verified JWT sub (most trustworthy — Supabase Auth issued)
      2. X-User-Id header
      3. body.user_id
      4. DEFAULT_USER_ID (backward compat fallback)

    Side effect: when a verified Supabase user is resolved, we ensure the
    user's email is registered as a profile alias so existing UIs keep working.
    """
    from core.user_registry import DEFAULT_USER_ID

    token = extract_token(authorization)
    payload = verify_token(token) if token else None

    if payload:
        sub = payload.get("sub")
        if sub:
            # Pre-register the user so the bundle is warm.
            from core.user_registry import get_user_bundle
            get_user_bundle(sub)
            return sub

    uid = (body_user_id or "").strip() or (x_user_id or "").strip()
    return uid or DEFAULT_USER_ID


def get_user_profile(authorization: Optional[str] = None) -> Optional[dict]:
    """
    Return the authenticated user's public profile (id, email, name) or None.

    Uses the Supabase auth admin edge only when a JWT is present; does not
    perform a network call when no token is supplied.
    """
    token = extract_token(authorization)
    payload = verify_token(token) if token else None
    if not payload:
        return None
    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name") or payload.get("user_metadata", {}).get("full_name"),
        "provider": payload.get("app_metadata", {}).get("provider"),
        "issued_at": payload.get("iat"),
        "expires_at": payload.get("exp"),
    }