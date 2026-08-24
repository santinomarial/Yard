from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import CurrentUser, create_access_token
from app.models.listing import Listing, ListingStatus
from app.models.marketplace_event import ListingEvent
from app.models.user import AppleIdentity, EmailVerification, User
from app.schemas.auth import (
    AppleSignInRequest,
    AuthResponse,
    DevelopmentSignInRequest,
    UserRead,
    UserUpdate,
    VerificationConfirm,
    VerificationRequest,
    VerificationRequested,
)
from app.services.apple_auth import AppleIdentityTokenVerifier, AppleTokenError
from app.services.email_verification import (
    VerificationError,
    confirm_verification,
    create_verification,
    get_email_provider,
)

router = APIRouter()
settings = get_settings()


def user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        display_name=user.display_name,
        harvard_email_verified=user.email_verified_at is not None,
        member_since=user.created_at,
        suspended=user.suspended_at is not None,
        admin=user.is_admin,
    )


def auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id), user=user_read(user))


@router.post("/development", response_model=AuthResponse)
async def development_sign_in(
    payload: DevelopmentSignInRequest, session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    if settings.environment != "development":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    subject = "development-admin" if payload.role == "admin" else "development-user"
    identity = await session.scalar(select(AppleIdentity).where(AppleIdentity.subject == subject))
    if identity:
        return auth_response(identity.user)
    user = User(
        display_name=payload.display_name,
        terms_accepted_at=datetime.now(UTC),
        email_verified_at=datetime.now(UTC) if payload.role == "admin" else None,
        is_admin=payload.role == "admin",
    )
    session.add(user)
    await session.flush()
    session.add(AppleIdentity(user=user, subject=subject))
    await session.commit()
    return auth_response(user)


@router.post("/apple", response_model=AuthResponse)
async def apple_sign_in(
    payload: AppleSignInRequest, session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    try:
        subject = await AppleIdentityTokenVerifier(settings.apple_audience).verify(
            payload.identity_token
        )
    except AppleTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_apple_token",
                "message": "Apple sign-in could not be verified.",
            },
        ) from None
    identity = await session.scalar(select(AppleIdentity).where(AppleIdentity.subject == subject))
    if identity:
        return auth_response(identity.user)
    user = User(display_name=payload.display_name or "Yard Member")
    session.add(user)
    await session.flush()
    session.add(AppleIdentity(user=user, subject=subject))
    await session.commit()
    return auth_response(user)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return user_read(user)


@router.patch("/profile", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    persisted = await session.get(User, user.id, with_for_update=True)
    if persisted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    persisted.display_name = payload.display_name.strip()
    await session.commit()
    return user_read(persisted)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Response:
    persisted = await session.get(User, user.id, with_for_update=True)
    if persisted is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    listings = await session.scalars(
        select(Listing).where(
            Listing.seller_id == user.id,
            Listing.status.not_in([ListingStatus.SOLD, ListingStatus.REMOVED]),
        )
    )
    for listing in listings:
        previous_status = listing.status
        listing.status = ListingStatus.REMOVED
        session.add(
            ListingEvent(
                listing_id=listing.id,
                actor_id=user.id,
                event_type="ListingRemovedForAccountDeletion",
                from_status=previous_status.value,
                to_status=ListingStatus.REMOVED.value,
            )
        )

    await session.execute(delete(AppleIdentity).where(AppleIdentity.user_id == user.id))
    await session.execute(delete(EmailVerification).where(EmailVerification.user_id == user.id))
    persisted.display_name = "Deleted Yard member"
    persisted.harvard_email = None
    persisted.email_verified_at = None
    persisted.terms_accepted_at = None
    persisted.is_admin = False
    persisted.deleted_at = datetime.now(UTC)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verification/request", response_model=VerificationRequested)
async def request_verification(
    payload: VerificationRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> VerificationRequested:
    try:
        _, code = await create_verification(
            session,
            user,
            payload.email,
            settings.allowed_harvard_domains,
            settings.verification_pepper,
            settings.verification_code_minutes,
            get_email_provider(),
        )
    except VerificationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error.code, "message": str(error)},
        ) from None
    return VerificationRequested(
        development_code=code if settings.environment == "development" else None
    )


@router.post("/verification/confirm", response_model=UserRead)
async def verify_email(
    payload: VerificationConfirm,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    try:
        await confirm_verification(
            session, user, payload.email, payload.code, settings.verification_pepper
        )
    except VerificationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error.code, "message": str(error)},
        ) from None
    return user_read(user)
