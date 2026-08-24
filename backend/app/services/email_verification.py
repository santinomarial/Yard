import asyncio
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, Protocol

import structlog
from botocore.session import Session  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
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


class SESEmailProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.ses_from_email:
            raise RuntimeError("YARD_SES_FROM_EMAIL is required in production")
        self.sender = settings.ses_from_email
        self.client: Any = Session().create_client("sesv2", region_name=settings.s3_region)

    async def send_verification(self, email: str, code: str) -> None:
        await asyncio.to_thread(
            self.client.send_email,
            FromEmailAddress=self.sender,
            Destination={"ToAddresses": [email]},
            Content={
                "Simple": {
                    "Subject": {"Data": "Your Yard verification code", "Charset": "UTF-8"},
                    "Body": {
                        "Text": {
                            "Data": (
                                f"Your Yard verification code is {code}. "
                                "It expires shortly. If you did not request it, ignore this email."
                            ),
                            "Charset": "UTF-8",
                        }
                    },
                }
            },
        )


@lru_cache
def get_email_provider() -> EmailProvider:
    if get_settings().environment == "production":
        return SESEmailProvider()
    return DevelopmentEmailProvider()


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
    await session.flush()
    try:
        await provider.send_verification(normalized, code)
    except Exception:
        await session.rollback()
        raise
    await session.commit()
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
    session.add(user)
    await session.commit()
