import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import AppleIdentity, AppReviewInvite, User


class ReviewAccessError(ValueError):
    pass


def hash_review_code(code: str, pepper: str) -> str:
    return hmac.new(pepper.encode(), f"app-review:{code}".encode(), hashlib.sha256).hexdigest()


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def marketplace_access_method(user: User) -> str:
    if user.email_verified_at is not None:
        return "harvard_email"
    if user.review_access_expires_at and as_utc(user.review_access_expires_at) > datetime.now(UTC):
        return "app_review"
    return "none"


def has_marketplace_access(user: User) -> bool:
    return marketplace_access_method(user) != "none"


async def create_review_invite(
    session: AsyncSession,
    *,
    purpose: str,
    created_by: str,
    lifetime_hours: int,
) -> tuple[AppReviewInvite, str]:
    if not 1 <= lifetime_hours <= 72:
        raise ValueError("Review invitations must expire in 1 to 72 hours")
    code = secrets.token_urlsafe(18)
    invite = AppReviewInvite(
        code_hash=hash_review_code(code, get_settings().verification_pepper),
        purpose=purpose,
        created_by=created_by,
        expires_at=datetime.now(UTC) + timedelta(hours=lifetime_hours),
    )
    session.add(invite)
    await session.commit()
    return invite, code


async def redeem_review_invite(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    code: str,
    pepper: str,
) -> User:
    async with session.begin():
        identity = await session.scalar(
            select(AppleIdentity).where(AppleIdentity.user_id == user_id)
        )
        if identity is None or identity.subject.startswith("development-"):
            raise ReviewAccessError("App Review access requires Sign in with Apple.")
        invite = await session.scalar(
            select(AppReviewInvite)
            .where(AppReviewInvite.code_hash == hash_review_code(code.strip(), pepper))
            .with_for_update()
        )
        now = datetime.now(UTC)
        if (
            invite is None
            or invite.consumed_at is not None
            or invite.revoked_at is not None
            or as_utc(invite.expires_at) <= now
        ):
            raise ReviewAccessError("That App Review access code is invalid or expired.")
        user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None or user.deleted_at is not None or user.suspended_at is not None:
            raise ReviewAccessError("That account cannot receive App Review access.")
        invite.consumed_at = now
        invite.consumed_by = user.id
        user.review_access_expires_at = invite.expires_at
    return user
