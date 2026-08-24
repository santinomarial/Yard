import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import CurrentUser
from app.schemas.pickup import PickupPresenceUpdate, PickupProposal, PickupRead
from app.services.analytics import record_event
from app.services.pickups import (
    PickupError,
    accept_pickup,
    cancel_pickup,
    confirm_exchange,
    get_pickup,
    propose_pickup,
    update_presence,
)

router = APIRouter()


def pickup_http_error(error: PickupError) -> HTTPException:
    if error.code.endswith("not_found"):
        code = status.HTTP_404_NOT_FOUND
    elif error.code.startswith("invalid_"):
        code = status.HTTP_422_UNPROCESSABLE_CONTENT
    else:
        code = status.HTTP_409_CONFLICT
    return HTTPException(
        status_code=code,
        detail={"code": error.code, "message": str(error)},
    )


@router.post("", response_model=PickupRead, status_code=201)
async def propose(
    payload: PickupProposal,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> PickupRead:
    try:
        pickup = await propose_pickup(
            session,
            payload.reservation_id,
            user.id,
            payload.meeting_zone,
            payload.proposed_for,
        )
    except PickupError as error:
        raise pickup_http_error(error) from None
    return PickupRead.model_validate(pickup)


@router.get("/{reservation_id}", response_model=PickupRead)
async def detail(
    reservation_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> PickupRead:
    try:
        pickup = await get_pickup(session, reservation_id, user.id)
    except PickupError as error:
        raise pickup_http_error(error) from None
    record_event(
        session,
        "pickup_scheduled",
        user_id=user.id,
        entity_type="pickup",
        entity_id=pickup.id,
    )
    await session.commit()
    return PickupRead.model_validate(pickup)


@router.post("/{reservation_id}/accept", response_model=PickupRead)
async def accept(
    reservation_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> PickupRead:
    try:
        pickup = await accept_pickup(session, reservation_id, user.id)
    except PickupError as error:
        raise pickup_http_error(error) from None
    return PickupRead.model_validate(pickup)


@router.patch("/{reservation_id}/presence", response_model=PickupRead)
async def presence(
    reservation_id: uuid.UUID,
    payload: PickupPresenceUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> PickupRead:
    try:
        pickup = await update_presence(
            session, reservation_id, user.id, payload.status, payload.eta_minutes
        )
    except PickupError as error:
        raise pickup_http_error(error) from None
    return PickupRead.model_validate(pickup)


@router.post("/{reservation_id}/complete", response_model=PickupRead)
async def complete(
    reservation_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> PickupRead:
    try:
        pickup = await confirm_exchange(session, reservation_id, user.id)
    except PickupError as error:
        raise pickup_http_error(error) from None
    if pickup.status.value == "completed":
        record_event(
            session,
            "exchange_completed",
            user_id=user.id,
            entity_type="pickup",
            entity_id=pickup.id,
        )
        await session.commit()
    return PickupRead.model_validate(pickup)


@router.post("/{reservation_id}/cancel", response_model=PickupRead)
async def cancel(
    reservation_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> PickupRead:
    try:
        pickup = await cancel_pickup(session, reservation_id, user.id)
    except PickupError as error:
        raise pickup_http_error(error) from None
    return PickupRead.model_validate(pickup)
