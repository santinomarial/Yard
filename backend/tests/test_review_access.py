from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import AppleIdentity, AppReviewInvite, User
from app.services.review_access import (
    ReviewAccessError,
    create_review_invite,
    has_marketplace_access,
    hash_review_code,
    marketplace_access_method,
    redeem_review_invite,
)


async def apple_user(session: AsyncSession) -> User:
    user = User(display_name="App Reviewer", terms_accepted_at=datetime.now(UTC))
    session.add(user)
    await session.flush()
    session.add(AppleIdentity(user_id=user.id, subject="apple-review-subject"))
    await session.commit()
    return user


async def test_review_invite_is_single_use_and_grants_temporary_access(
    session: AsyncSession,
) -> None:
    user = await apple_user(session)
    invite, code = await create_review_invite(
        session, purpose="App Store build 1", created_by="release-operator", lifetime_hours=48
    )

    updated = await redeem_review_invite(
        session,
        user_id=user.id,
        code=code,
        pepper=get_settings().verification_pepper,
    )

    assert updated.review_access_expires_at == invite.expires_at
    assert has_marketplace_access(updated)
    assert marketplace_access_method(updated) == "app_review"
    with pytest.raises(ReviewAccessError):
        await redeem_review_invite(
            session,
            user_id=user.id,
            code=code,
            pepper=get_settings().verification_pepper,
        )


async def test_expired_review_invite_is_rejected(session: AsyncSession) -> None:
    user = await apple_user(session)
    session.add(
        AppReviewInvite(
            code_hash=hash_review_code("expired-review-code", get_settings().verification_pepper),
            purpose="Expired review",
            created_by="release-operator",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    await session.commit()

    with pytest.raises(ReviewAccessError):
        await redeem_review_invite(
            session,
            user_id=user.id,
            code="expired-review-code",
            pepper=get_settings().verification_pepper,
        )
