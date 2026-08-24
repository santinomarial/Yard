import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import CurrentUser
from app.models.notification import DeviceToken, NotificationOutbox
from app.schemas.notification import DeviceTokenCreate, DeviceTokenRead, NotificationRead

router = APIRouter()


@router.post("/devices", response_model=DeviceTokenRead)
async def register_device(
    payload: DeviceTokenCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> DeviceToken:
    token = payload.token.lower()
    device = await session.scalar(select(DeviceToken).where(DeviceToken.token == token))
    if device is None:
        device = DeviceToken(
            user_id=user.id, token=token, environment=payload.environment, is_active=True
        )
        session.add(device)
    else:
        device.user_id = user.id
        device.environment = payload.environment
        device.is_active = True
    await session.commit()
    return device


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_device(
    device_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Response:
    device = await session.scalar(
        select(DeviceToken).where(DeviceToken.id == device_id, DeviceToken.user_id == user.id)
    )
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    device.is_active = False
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[NotificationRead])
async def notifications(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[NotificationOutbox]:
    rows = await session.scalars(
        select(NotificationOutbox)
        .where(NotificationOutbox.user_id == user.id)
        .order_by(NotificationOutbox.created_at.desc())
        .limit(100)
    )
    return list(rows.all())
