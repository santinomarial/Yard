import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Protocol

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import EmailVerification, User

logger = structlog.get_logger()


class VerificationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class EmailProvider(Protocol):
    async def send_verification(self, email: str, code: str) -> None: ...


class DevelopmentEmailProvider:
    async def send_verification(self, email: str, code: str) -> None:
        logger.info("development_verification_email", email=email, code=code)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_harvard_email(email: str, allowed_domains: list[str]) -> str:
    normalized = normalize_email(email)
    if normalized.count("@") != 1:
        raise VerificationError("invalid_email", "Enter a valid Harvard email address.")
    domain = normalized.rsplit("@", 1)[1]
    if domain not in {item.lower() for item in allowed_domains}:
        raise VerificationError(
            "email_domain_not_allowed", "Use an eligible Harvard-managed email address."
        )
    return normalized


def hash_code(code: str, pepper: str) -> str:
    return hmac.new(pepper.encode(), code.encode(), hashlib.sha256).hexdigest()


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def create_verification(
    session: AsyncSession,
    user: User,
    email: str,
    allowed_domains: list[str],
    pepper: str,
    lifetime_minutes: int,
    provider: EmailProvider,
) -> tuple[EmailVerification, str]:
    normalized = validate_harvard_email(email, allowed_domains)
    latest = await session.scalar(
        select(EmailVerification)
        .where(EmailVerification.user_id == user.id)
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )
    now = datetime.now(UTC)
    if latest and as_utc(latest.created_at) > now - timedelta(seconds=60):
        raise VerificationError("code_rate_limited", "Wait before requesting another code.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    verification = EmailVerification(
        user_id=user.id,
        email=normalized,
        code_hash=hash_code(code, pepper),
        expires_at=now + timedelta(minutes=lifetime_minutes),
    )
    session.add(verification)
    await session.commit()
    await provider.send_verification(normalized, code)
    return verification, code


async def confirm_verification(
    session: AsyncSession, user: User, email: str, code: str, pepper: str
) -> None:
    normalized = normalize_email(email)
    verification = await session.scalar(
        select(EmailVerification)
        .where(
            EmailVerification.user_id == user.id,
            EmailVerification.email == normalized,
            EmailVerification.consumed_at.is_(None),
        )
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )
    now = datetime.now(UTC)
    if verification is None or as_utc(verification.expires_at) < now:
        raise VerificationError("code_expired", "Request a new verification code.")
    if verification.attempts >= 5:
        raise VerificationError("too_many_attempts", "Request a new verification code.")
    verification.attempts += 1
    if not hmac.compare_digest(verification.code_hash, hash_code(code, pepper)):
        await session.commit()
        raise VerificationError("invalid_code", "That verification code is not valid.")
    verification.consumed_at = now
    user.harvard_email = normalized
    user.email_verified_at = now
    await session.commit()
