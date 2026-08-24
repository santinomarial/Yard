import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing, ListingStatus
from app.models.marketplace_event import ListingEvent
from app.models.pickup import ArrivalStatus, PickupSession, PickupStatus
from app.models.reservation import Reservation, ReservationStatus
from app.services.listing_lifecycle import transition_listing
from app.services.reservations import release_or_promote

PUBLIC_PICKUP_ZONES = frozenset(
    {
        "Adams House area",
        "Cabot House area",
        "Currier House area",
        "Eliot House area",
        "Harvard Square",
        "Kirkland House area",
        "Leverett House area",
        "Quincy House area",
        "SEC",
        "Smith Campus Center area",
        "Quad",
    }
)


class PickupError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def require_participant(reservation: Reservation | None, actor_id: uuid.UUID) -> Reservation:
    if reservation is None or actor_id not in {reservation.buyer_id, reservation.seller_id}:
        raise PickupError("pickup_not_found", "This pickup is unavailable.")
    return reservation


def pickup_event(
    reservation: Reservation,
    actor_id: uuid.UUID,
    event_type: str,
    pickup: PickupSession,
    extra: dict[str, object] | None = None,
) -> ListingEvent:
    data: dict[str, object] = {"pickup_id": str(pickup.id)}
    if extra:
        data.update(extra)
    return ListingEvent(
        listing_id=reservation.listing_id,
        actor_id=actor_id,
        event_type=event_type,
        event_data=data,
    )


async def get_pickup(
    session: AsyncSession, reservation_id: uuid.UUID, actor_id: uuid.UUID
) -> PickupSession:
    reservation = require_participant(await session.get(Reservation, reservation_id), actor_id)
    pickup = await session.scalar(
        select(PickupSession).where(PickupSession.reservation_id == reservation.id)
    )
    if pickup is None:
        raise PickupError("pickup_not_found", "This pickup is unavailable.")
    return pickup


async def propose_pickup(
    session: AsyncSession,
    reservation_id: uuid.UUID,
    actor_id: uuid.UUID,
    meeting_zone: str,
    proposed_for: datetime,
) -> PickupSession:
    now = datetime.now(UTC)
    if meeting_zone not in PUBLIC_PICKUP_ZONES:
        raise PickupError("invalid_pickup_zone", "Choose one of Yard's public pickup areas.")
    if proposed_for.tzinfo is None or not now + timedelta(
        minutes=15
    ) <= proposed_for <= now + timedelta(days=7):
        raise PickupError("invalid_pickup_time", "Choose a time from 15 minutes to 7 days away.")

    async with session.begin():
        reservation = require_participant(
            await session.scalar(
                select(Reservation).where(Reservation.id == reservation_id).with_for_update()
            ),
            actor_id,
        )
        if reservation.status != ReservationStatus.ACTIVE:
            raise PickupError("reservation_not_active", "This reservation is no longer active.")
        pickup = await session.scalar(
            select(PickupSession)
            .where(PickupSession.reservation_id == reservation.id)
            .with_for_update()
        )
        if pickup is None:
            pickup = PickupSession(
                id=uuid.uuid4(),
                reservation_id=reservation.id,
                proposed_by=actor_id,
                meeting_zone=meeting_zone,
                proposed_for=proposed_for,
                status=PickupStatus.PROPOSED,
            )
            session.add(pickup)
        elif pickup.status == PickupStatus.PROPOSED:
            pickup.proposed_by = actor_id
            pickup.meeting_zone = meeting_zone
            pickup.proposed_for = proposed_for
        else:
            raise PickupError("pickup_not_editable", "This pickup can no longer be changed.")
        session.add(
            pickup_event(
                reservation,
                actor_id,
                "PickupProposed",
                pickup,
                {"meeting_zone": meeting_zone, "proposed_for": proposed_for.isoformat()},
            )
        )
    return pickup


async def accept_pickup(
    session: AsyncSession, reservation_id: uuid.UUID, actor_id: uuid.UUID
) -> PickupSession:
    async with session.begin():
        reservation = require_participant(
            await session.scalar(
                select(Reservation).where(Reservation.id == reservation_id).with_for_update()
            ),
            actor_id,
        )
        pickup = await session.scalar(
            select(PickupSession)
            .where(PickupSession.reservation_id == reservation.id)
            .with_for_update()
        )
        if (
            reservation.status != ReservationStatus.ACTIVE
            or pickup is None
            or pickup.status != PickupStatus.PROPOSED
        ):
            raise PickupError("pickup_not_accepting", "This pickup proposal is unavailable.")
        if pickup.proposed_by == actor_id:
            raise PickupError(
                "pickup_self_accept", "The other participant must accept the proposal."
            )
        now = datetime.now(UTC)
        if utc(pickup.proposed_for) <= now:
            raise PickupError("pickup_time_passed", "Propose a new pickup time.")
        pickup.status = PickupStatus.SCHEDULED
        pickup.accepted_at = now
        reservation.expires_at = utc(pickup.proposed_for) + timedelta(hours=2)
        session.add(pickup_event(reservation, actor_id, "PickupScheduled", pickup))
    return pickup


async def update_presence(
    session: AsyncSession,
    reservation_id: uuid.UUID,
    actor_id: uuid.UUID,
    arrival: ArrivalStatus,
    eta_minutes: int | None,
) -> PickupSession:
    if arrival == ArrivalStatus.ARRIVED:
        eta_minutes = 0
    async with session.begin():
        reservation = require_participant(
            await session.scalar(
                select(Reservation).where(Reservation.id == reservation_id).with_for_update()
            ),
            actor_id,
        )
        pickup = await session.scalar(
            select(PickupSession)
            .where(PickupSession.reservation_id == reservation.id)
            .with_for_update()
        )
        if pickup is None or pickup.status != PickupStatus.SCHEDULED:
            raise PickupError("pickup_not_scheduled", "This pickup is not scheduled.")
        if actor_id == reservation.buyer_id:
            pickup.buyer_arrival = arrival
            pickup.buyer_eta_minutes = eta_minutes
        else:
            pickup.seller_arrival = arrival
            pickup.seller_eta_minutes = eta_minutes
        session.add(
            pickup_event(
                reservation,
                actor_id,
                "PickupStatusUpdated",
                pickup,
                {"status": arrival.value, "eta_minutes": eta_minutes},
            )
        )
    return pickup


async def confirm_exchange(
    session: AsyncSession, reservation_id: uuid.UUID, actor_id: uuid.UUID
) -> PickupSession:
    async with session.begin():
        reservation = require_participant(
            await session.scalar(
                select(Reservation).where(Reservation.id == reservation_id).with_for_update()
            ),
            actor_id,
        )
        pickup = await session.scalar(
            select(PickupSession)
            .where(PickupSession.reservation_id == reservation.id)
            .with_for_update()
        )
        if (
            reservation.status != ReservationStatus.ACTIVE
            or pickup is None
            or pickup.status != PickupStatus.SCHEDULED
        ):
            raise PickupError("pickup_not_completable", "This pickup cannot be completed.")
        now = datetime.now(UTC)
        if actor_id == reservation.buyer_id:
            pickup.buyer_confirmed_at = pickup.buyer_confirmed_at or now
        else:
            pickup.seller_confirmed_at = pickup.seller_confirmed_at or now
        session.add(pickup_event(reservation, actor_id, "ExchangeCompletionConfirmed", pickup))
        if pickup.buyer_confirmed_at and pickup.seller_confirmed_at:
            listing = await session.scalar(
                select(Listing)
                .where(Listing.id == reservation.listing_id)
                .with_for_update(of=Listing)
            )
            if listing is None or listing.status != ListingStatus.RESERVED:
                raise PickupError("stale_listing_state", "The listing state changed.")
            pickup.status = PickupStatus.COMPLETED
            pickup.completed_at = now
            reservation.status = ReservationStatus.COMPLETED
            reservation.completed_at = now
            session.add(
                transition_listing(
                    listing,
                    ListingStatus.SOLD,
                    actor_id,
                    "ExchangeCompleted",
                    {"reservation_id": str(reservation.id), "pickup_id": str(pickup.id)},
                )
            )
    return pickup


async def cancel_pickup(
    session: AsyncSession, reservation_id: uuid.UUID, actor_id: uuid.UUID
) -> PickupSession:
    async with session.begin():
        reservation = require_participant(
            await session.scalar(
                select(Reservation).where(Reservation.id == reservation_id).with_for_update()
            ),
            actor_id,
        )
        pickup = await session.scalar(
            select(PickupSession)
            .where(PickupSession.reservation_id == reservation.id)
            .with_for_update()
        )
        if (
            reservation.status != ReservationStatus.ACTIVE
            or pickup is None
            or pickup.status not in {PickupStatus.PROPOSED, PickupStatus.SCHEDULED}
        ):
            raise PickupError("pickup_not_cancellable", "This pickup cannot be cancelled.")
        listing = await session.scalar(
            select(Listing).where(Listing.id == reservation.listing_id).with_for_update(of=Listing)
        )
        if listing is None or listing.status != ListingStatus.RESERVED:
            raise PickupError("stale_listing_state", "The listing state changed.")
        pickup.status = PickupStatus.CANCELLED
        pickup.cancelled_at = datetime.now(UTC)
        reservation.status = ReservationStatus.CANCELLED
        session.add(pickup_event(reservation, actor_id, "PickupCancelled", pickup))
        await release_or_promote(session, listing, actor_id, "ReservationCancelled")
    return pickup
