import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing, ListingStatus
from app.models.reservation import Reservation, ReservationStatus
from app.services.listing_lifecycle import transition_listing


class ReservationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


async def reserve_listing(
    session: AsyncSession,
    listing_id: uuid.UUID,
    buyer_id: uuid.UUID,
    idempotency_key: str,
    lease_minutes: int = 30,
) -> tuple[Reservation, bool]:
    async with session.begin():
        existing = await session.scalar(
            select(Reservation).where(
                Reservation.buyer_id == buyer_id,
                Reservation.idempotency_key == idempotency_key,
            )
        )
        if existing:
            if existing.listing_id != listing_id:
                raise ReservationError(
                    "idempotency_key_reused",
                    "This request key was already used for another listing.",
                )
            return existing, False

        listing = await session.scalar(
            select(Listing).where(Listing.id == listing_id).with_for_update(of=Listing)
        )
        if listing is None:
            raise ReservationError("listing_not_found", "This listing is unavailable.")

        # A same-key retry can arrive after its first request committed while this request waited.
        existing = await session.scalar(
            select(Reservation).where(
                Reservation.buyer_id == buyer_id,
                Reservation.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return existing, False
        if listing.seller_id == buyer_id:
            raise ReservationError("seller_cannot_reserve", "You cannot reserve your own listing.")
        if listing.status != ListingStatus.ACTIVE:
            raise ReservationError(
                "listing_already_reserved", "This item was reserved by another buyer."
            )

        now = datetime.now(UTC)
        reservation_id = uuid.uuid4()
        reservation = Reservation(
            id=reservation_id,
            listing_id=listing.id,
            buyer_id=buyer_id,
            seller_id=listing.seller_id,
            status=ReservationStatus.ACTIVE,
            idempotency_key=idempotency_key,
            expires_at=now + timedelta(minutes=lease_minutes),
        )
        session.add(reservation)
        session.add(
            transition_listing(
                listing,
                ListingStatus.RESERVED,
                buyer_id,
                "ListingReserved",
                {"reservation_id": str(reservation_id)},
            )
        )
    return reservation, True


async def cancel_reservation(
    session: AsyncSession, reservation_id: uuid.UUID, actor_id: uuid.UUID
) -> Reservation:
    async with session.begin():
        reservation = await session.scalar(
            select(Reservation).where(Reservation.id == reservation_id).with_for_update()
        )
        if reservation is None or actor_id not in {reservation.buyer_id, reservation.seller_id}:
            raise ReservationError("reservation_not_found", "This reservation is unavailable.")
        if reservation.status != ReservationStatus.ACTIVE:
            raise ReservationError(
                "reservation_not_active", "This reservation is no longer active."
            )
        listing = await session.scalar(
            select(Listing).where(Listing.id == reservation.listing_id).with_for_update(of=Listing)
        )
        if listing is None or listing.status != ListingStatus.RESERVED:
            raise ReservationError("stale_listing_state", "The listing state changed.")
        reservation.status = ReservationStatus.CANCELLED
        session.add(
            transition_listing(
                listing,
                ListingStatus.ACTIVE,
                actor_id,
                "ReservationCancelled",
                {"reservation_id": str(reservation.id)},
            )
        )
    return reservation


async def expire_due_reservations(session: AsyncSession, limit: int = 100) -> int:
    expired = 0
    async with session.begin():
        reservations = await session.scalars(
            select(Reservation)
            .where(
                Reservation.status == ReservationStatus.ACTIVE,
                Reservation.expires_at <= datetime.now(UTC),
            )
            .order_by(Reservation.expires_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        for reservation in reservations:
            listing = await session.scalar(
                select(Listing)
                .where(Listing.id == reservation.listing_id)
                .with_for_update(of=Listing)
            )
            if listing is None or listing.status != ListingStatus.RESERVED:
                continue
            reservation.status = ReservationStatus.EXPIRED
            session.add(
                transition_listing(
                    listing,
                    ListingStatus.ACTIVE,
                    reservation.buyer_id,
                    "ReservationExpired",
                    {"reservation_id": str(reservation.id)},
                )
            )
            expired += 1
    return expired
