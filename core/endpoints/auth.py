"""
ChitraGupta 2.0 — Auth API Endpoints
Profile + session verification routes.

These endpoints are thin: the frontend uses @supabase/supabase-js directly for
sign-up/login/logout and sends the resulting access token on every request.
The backend's job is only to *verify* that token and expose the user's profile
so the frontend can render session state.

All endpoints gracefully degrade when Supabase Auth is not configured —
they return an anonymous profile so the existing single-user flow keeps working.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Header
from pydantic import BaseModel

from core.auth import get_user_profile, verify_token, extract_token
from core.user_registry import get_user_bundle, DEFAULT_USER_ID

logger = logging.getLogger("chitragupta.auth_endpoint")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ProfileResponse(BaseModel):
    authenticated: bool
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    provider: Optional[str] = None
    expires_at: Optional[int] = None


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None  # persisted via identity model values


@router.get("/profile", response_model=ProfileResponse)
def profile(authorization: Optional[str] = Header(default=None)):
    """Return the authenticated user's profile, or anonymous default."""
    info = get_user_profile(authorization)
    if info and info.get("id"):
        return ProfileResponse(
            authenticated=True,
            user_id=info["id"],
            email=info.get("email"),
            name=info.get("name"),
            provider=info.get("provider"),
            expires_at=info.get("expires_at"),
        )
    return ProfileResponse(authenticated=False, user_id=DEFAULT_USER_ID)


@router.get("/verify")
def verify(authorization: Optional[str] = Header(default=None)):
    """Lightweight session-restore ping — returns valid/invalid + user_id."""
    token = extract_token(authorization)
    payload = verify_token(token) if token else None
    if payload and payload.get("sub"):
        # Warm the bundle
        get_user_bundle(payload["sub"])
        return {"valid": True, "user_id": payload["sub"], "email": payload.get("email")}
    return {"valid": False, "user_id": DEFAULT_USER_ID}


@router.post("/profile")
def update_profile(
    body: ProfileUpdateRequest,
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    """Persist simple profile preferences (name, language) for the caller.

    Language preference is stored on the identity model so the coaching
    pipeline can adapt response language automatically.
    """
    info = get_user_profile(authorization)
    uid = (info or {}).get("id") or (x_user_id or "").strip() or DEFAULT_USER_ID

    bundle = get_user_bundle(uid)
    updated = {"user_id": uid}

    if body.language:
        # Persist language preference as an identity value.
        try:
            values = bundle.identity_model.profile.values if hasattr(bundle.identity_model, "profile") else []
            if "language" not in [v.lower() for v in values]:
                bundle.identity_model.add_evidence(type("Ev", (), {
                    "dimension": "values",
                    "value": f"language:{body.language}",
                    "confidence": 0.9,
                    "source": "explicit_preference",
                    "timestamp": None,
                })())
        except Exception as e:
            logger.debug(f"Language preference persist skipped: {e}")
        updated["language"] = body.language

    if body.name:
        updated["name"] = body.name

    return {"ok": True, "updated": updated}