import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import CurrentUser
from app.schemas.reservation import ReservationCreate, ReservationRead
from app.services.reservations import ReservationError, cancel_reservation, reserve_listing

router = APIRouter()


def reservation_http_error(error: ReservationError) -> HTTPException:
    not_found = error.code.endswith("not_found")
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND if not_found else status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": str(error)},
    )


@router.post("", response_model=ReservationRead)
async def create_reservation(
    payload: ReservationCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ReservationRead:
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "harvard_email_required",
                "message": "Verify a Harvard email before reserving an item.",
            },
        )
    try:
        reservation, _ = await reserve_listing(
            session, payload.listing_id, user.id, payload.idempotency_key
        )
    except ReservationError as error:
        raise reservation_http_error(error) from None
    return ReservationRead.model_validate(reservation)


@router.post("/{reservation_id}/cancel", response_model=ReservationRead)
async def cancel(
    reservation_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ReservationRead:
    try:
        reservation = await cancel_reservation(session, reservation_id, user.id)
    except ReservationError as error:
        raise reservation_http_error(error) from None
    return ReservationRead.model_validate(reservation)
