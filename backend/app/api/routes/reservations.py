import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.metrics import metrics
from app.core.security import CurrentUser
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate, ReservationRead, WaitlistRead
from app.services.analytics import record_event
from app.services.notifications import enqueue_notification
from app.services.reservations import (
    ReservationError,
    cancel_reservation,
    claim_waitlist_offer,
    join_waitlist,
    reserve_listing,
)

router = APIRouter()


def reservation_http_error(error: ReservationError) -> HTTPException:
    not_found = error.code.endswith("not_found")
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND if not_found else status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": str(error)},
    )


@router.get("/mine", response_model=list[ReservationRead])
async def my_reservations(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[Reservation]:
    rows = await session.scalars(
        select(Reservation)
        .where(or_(Reservation.buyer_id == user.id, Reservation.seller_id == user.id))
        .order_by(Reservation.created_at.desc())
        .limit(100)
    )
    return list(rows.all())


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
        metrics.increment("reservation_conflicts_total", code=error.code)
        raise reservation_http_error(error) from None
    record_event(
        session,
        "reservation_succeeded",
        user_id=user.id,
        entity_type="reservation",
        entity_id=reservation.id,
        properties={"listing_id": str(reservation.listing_id)},
    )
    await enqueue_notification(
        session,
        user_id=reservation.buyer_id,
        notification_type="reservation_confirmed",
        title="Item reserved",
        body="Your reservation is confirmed. Coordinate a public pickup with the seller.",
        idempotency_key=f"reservation-confirmed:{reservation.id}:buyer",
        deep_link=f"yard://reservations/{reservation.id}",
    )
    await enqueue_notification(
        session,
        user_id=reservation.seller_id,
        notification_type="seller_response",
        title="Your item was reserved",
        body="A buyer is ready to coordinate pickup.",
        idempotency_key=f"reservation-confirmed:{reservation.id}:seller",
        deep_link=f"yard://reservations/{reservation.id}",
    )
    await session.commit()
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


@router.put("/waitlist/{listing_id}", response_model=WaitlistRead)
async def join(
    listing_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> WaitlistRead:
    try:
        entry = await join_waitlist(session, listing_id, user.id)
    except ReservationError as error:
        raise reservation_http_error(error) from None
    return WaitlistRead.model_validate(entry)


@router.post("/waitlist/offers/{entry_id}/claim", response_model=ReservationRead)
async def claim_offer(
    entry_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ReservationRead:
    try:
        reservation = await claim_waitlist_offer(session, entry_id, user.id)
    except ReservationError as error:
        raise reservation_http_error(error) from None
    return ReservationRead.model_validate(reservation)
