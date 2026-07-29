"""Resolves the current doctor from a Supabase-issued JWT.

The frontend (Supabase Auth) sends `Authorization: Bearer <access_token>`.
When `SUPABASE_JWT_SECRET` isn't configured (local dev without Supabase),
this falls back to an anonymous demo doctor so the Extractor/Safety
pipeline remains usable without a database.
"""
from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, Header

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

_DEMO_DOCTOR_ID = "00000000-0000-0000-0000-000000000000"
_DEMO_DOCTOR_NAME = "Dr. Demo"


class AuthError(AppError):
    status_code = 401
    error_code = "unauthorized"


@dataclass
class CurrentDoctor:
    id: str
    name: str
    email: str | None = None


def get_current_doctor(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> CurrentDoctor:
    if not settings.supabase_jwt_secret:
        return CurrentDoctor(id=_DEMO_DOCTOR_ID, name=_DEMO_DOCTOR_NAME)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing bearer token")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise AuthError(f"Invalid token: {exc}") from exc

    user_metadata = payload.get("user_metadata", {})
    return CurrentDoctor(
        id=payload["sub"],
        name=user_metadata.get("full_name", payload.get("email", "Doctor")),
        email=payload.get("email"),
    )
