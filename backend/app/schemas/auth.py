import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DevelopmentSignInRequest(BaseModel):
    display_name: str = Field(default="Alex Rivers", min_length=1, max_length=80)
    role: Literal["member", "admin"] = "member"
    fixture_id: str | None = Field(default=None, pattern=r"^[a-z0-9-]{1,40}$")


class AppleSignInRequest(BaseModel):
    identity_token: str = Field(min_length=20, max_length=10_000)
    display_name: str | None = Field(default=None, min_length=1, max_length=80)


class UserRead(BaseModel):
    id: uuid.UUID
    display_name: str
    harvard_email_verified: bool
    marketplace_access_granted: bool
    access_method: Literal["none", "harvard_email", "app_review"]
    member_since: datetime
    suspended: bool
    admin: bool


class UserUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class VerificationRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


class VerificationRequested(BaseModel):
    accepted: bool = True
    development_code: str | None = None


class VerificationConfirm(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    code: str = Field(pattern=r"^\d{6}$")


class ReviewAccessRequest(BaseModel):
    code: str = Field(min_length=12, max_length=80)
