import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bundle import Bundle, BundleItem, BundleReservation
from app.models.listing import Listing, ListingStatus
from app.models.reservation import Reservation, ReservationStatus
from app.services.listing_lifecycle import transition_listing
from app.services.reservations import ReservationError


async def reserve_bundle(
    session: AsyncSession,
    bundle_id: uuid.UUID,
    buyer_id: uuid.UUID,
    idempotency_key: str,
    lease_minutes: int = 30,
) -> tuple[BundleReservation, bool]:
    async with session.begin():
        existing = await session.scalar(
            select(BundleReservation).where(
                BundleReservation.buyer_id == buyer_id,
                BundleReservation.idempotency_key == idempotency_key,
            )
        )
        if existing:
            if existing.bundle_id != bundle_id:
                raise ReservationError(
                    "idempotency_key_reused", "This request key was used for another bundle."
                )
            return existing, False
        bundle = await session.scalar(
            select(Bundle).where(Bundle.id == bundle_id).with_for_update()
        )
        if bundle is None or not bundle.is_active:
            raise ReservationError("bundle_unavailable", "This bundle is unavailable.")
        if bundle.seller_id == buyer_id:
            raise ReservationError("seller_cannot_reserve", "You cannot reserve your own bundle.")
        item_ids = list(
            (
                await session.scalars(
                    select(BundleItem.listing_id)
                    .where(BundleItem.bundle_id == bundle.id)
                    .order_by(BundleItem.listing_id)
                )
            ).all()
        )
        if not item_ids:
            raise ReservationError("bundle_empty", "This bundle has no items.")
        listings = list(
            (
                await session.scalars(
                    select(Listing)
                    .where(Listing.id.in_(item_ids))
                    .order_by(Listing.id)
                    .with_for_update(of=Listing)
                )
            )
            .unique()
            .all()
        )
        if len(listings) != len(item_ids) or any(
            listing.status != ListingStatus.ACTIVE or listing.seller_id != bundle.seller_id
            for listing in listings
        ):
            raise ReservationError(
                "bundle_inventory_unavailable", "One or more bundle items are unavailable."
            )
        now = datetime.now(UTC)
        bundle_reservation = BundleReservation(
            id=uuid.uuid4(),
            bundle_id=bundle.id,
            buyer_id=buyer_id,
            idempotency_key=idempotency_key,
            expires_at=now + timedelta(minutes=lease_minutes),
        )
        session.add(bundle_reservation)
        for listing in listings:
            reservation = Reservation(
                id=uuid.uuid4(),
                listing_id=listing.id,
                buyer_id=buyer_id,
                seller_id=bundle.seller_id,
                bundle_reservation_id=bundle_reservation.id,
                status=ReservationStatus.ACTIVE,
                idempotency_key=f"bundle:{bundle_reservation.id}:{listing.id}",
                expires_at=bundle_reservation.expires_at,
            )
            session.add(reservation)
            session.add(
                transition_listing(
                    listing,
                    ListingStatus.RESERVED,
                    buyer_id,
                    "BundleItemReserved",
                    {
                        "bundle_id": str(bundle.id),
                        "bundle_reservation_id": str(bundle_reservation.id),
                    },
                )
            )
        bundle.is_active = False
    return bundle_reservation, True
