import jwt
import pytest

from app.core.auth import AuthError, _DEMO_DOCTOR_ID, get_current_doctor
from app.core.config import Settings


def test_get_current_doctor_falls_back_to_demo_without_jwt_secret():
    settings = Settings(supabase_jwt_secret="")
    doctor = get_current_doctor(authorization=None, settings=settings)
    assert doctor.id == _DEMO_DOCTOR_ID


def test_get_current_doctor_requires_bearer_token_when_configured():
    settings = Settings(supabase_jwt_secret="test-secret")
    with pytest.raises(AuthError):
        get_current_doctor(authorization=None, settings=settings)


def test_get_current_doctor_decodes_valid_token():
    settings = Settings(supabase_jwt_secret="test-secret")
    token = jwt.encode(
        {"sub": "doctor-123", "email": "doc@watanhospital.af", "aud": "authenticated"},
        "test-secret",
        algorithm="HS256",
    )
    doctor = get_current_doctor(authorization=f"Bearer {token}", settings=settings)
    assert doctor.id == "doctor-123"
    assert doctor.email == "doc@watanhospital.af"


def test_get_current_doctor_rejects_invalid_token():
    settings = Settings(supabase_jwt_secret="test-secret")
    with pytest.raises(AuthError):
        get_current_doctor(authorization="Bearer not-a-real-token", settings=settings)
