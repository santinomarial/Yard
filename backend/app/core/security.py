import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/apple")
settings = get_settings()


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=7), "iss": "yard"},
        settings.access_token_secret,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> uuid.UUID:
    claims = jwt.decode(
        token,
        settings.access_token_secret,
        algorithms=["HS256"],
        issuer="yard",
    )
    return uuid.UUID(claims["sub"])


async def current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "invalid_token", "message": "Sign in again to continue."},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token)
    except (InvalidTokenError, KeyError, ValueError):
        raise credentials_error from None
    user = await session.get(User, user_id)
    if user is None or user.suspended_at is not None or user.deleted_at is not None:
        await session.rollback()
        raise credentials_error
    session.expunge(user)
    await session.rollback()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def current_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "admin_required", "message": "Moderator access is required."},
        )
    return user


AdminUser = Annotated[User, Depends(current_admin)]
