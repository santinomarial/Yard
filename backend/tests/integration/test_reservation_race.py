import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.database import SessionFactory
from app.models import (
    Category,
    Listing,
    ListingCondition,
    ListingStatus,
    Reservation,
    User,
    WaitlistEntry,
    WaitlistStatus,
)
from app.services.reservations import (
    ReservationError,
    cancel_reservation,
    claim_waitlist_offer,
    join_waitlist,
    reserve_listing,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]


async def setup_inventory() -> tuple[uuid.UUID, list[uuid.UUID]]:
    async with SessionFactory() as session, session.begin():
        category = Category(
            name=f"Race {uuid.uuid4().hex[:8]}",
            slug=f"race-{uuid.uuid4().hex}",
            symbol="bolt",
        )
        seller = User(
            display_name="Race Seller",
            email_verified_at=datetime.now(UTC),
        )
        buyers = [
            User(display_name=f"Buyer {index}", email_verified_at=datetime.now(UTC))
            for index in range(20)
        ]
        session.add_all([category, seller, *buyers])
        await session.flush()
        listing = Listing(
            seller_id=seller.id,
            title="Concurrency Test Monitor",
            description="Inventory used only by the PostgreSQL race test.",
            category=category,
            price_cents=8_500,
            is_free=False,
            condition=ListingCondition.GOOD,
            status=ListingStatus.ACTIVE,
            pickup_zone="Harvard Square",
            published_at=datetime.now(UTC),
        )
        session.add(listing)
        await session.flush()
        return listing.id, [buyer.id for buyer in buyers]


async def attempt(listing_id: uuid.UUID, buyer_id: uuid.UUID, key: str) -> str:
    async with SessionFactory() as session:
        try:
            reservation, created = await reserve_listing(session, listing_id, buyer_id, key)
            return f"success:{reservation.id}:{created}"
        except ReservationError as error:
            return f"conflict:{error.code}"


async def test_exactly_one_concurrent_reservation_succeeds() -> None:
    listing_id, buyers = await setup_inventory()
    results = await asyncio.gather(
        *(
            attempt(listing_id, buyer, f"race-{index}-{uuid.uuid4()}")
            for index, buyer in enumerate(buyers)
        )
    )
    assert sum(result.startswith("success") for result in results) == 1
    assert all(
        result.startswith("success") or result == "conflict:listing_already_reserved"
        for result in results
    )
    async with SessionFactory() as session:
        reservations = list(
            (
                await session.scalars(
                    select(Reservation).where(Reservation.listing_id == listing_id)
                )
            ).all()
        )
        listing = await session.get(Listing, listing_id)
        assert len(reservations) == 1
        assert listing is not None and listing.status == ListingStatus.RESERVED


async def test_same_idempotency_key_has_one_logical_effect() -> None:
    listing_id, buyers = await setup_inventory()
    buyer = buyers[0]
    key = f"retry-{uuid.uuid4()}"
    results = await asyncio.gather(*(attempt(listing_id, buyer, key) for _ in range(10)))
    reservation_ids = {result.split(":")[1] for result in results if result.startswith("success")}
    assert len(reservation_ids) == 1
    assert sum(result.endswith(":True") for result in results) == 1


async def test_waitlist_promotion_keeps_inventory_from_direct_buyers() -> None:
    listing_id, buyers = await setup_inventory()
    async with SessionFactory() as session:
        first, _ = await reserve_listing(session, listing_id, buyers[0], f"first-{uuid.uuid4()}")
    async with SessionFactory() as session:
        first_in_line = await join_waitlist(session, listing_id, buyers[1])
    async with SessionFactory() as session:
        await join_waitlist(session, listing_id, buyers[2])
    async with SessionFactory() as session:
        await cancel_reservation(session, first.id, buyers[0])

    async with SessionFactory() as session:
        promoted = await session.get(WaitlistEntry, first_in_line.id)
        listing = await session.get(Listing, listing_id)
        assert promoted is not None and promoted.status == WaitlistStatus.OFFERED
        assert listing is not None and listing.status == ListingStatus.RESERVED

    direct = await attempt(listing_id, buyers[3], f"direct-{uuid.uuid4()}")
    assert direct == "conflict:listing_already_reserved"
    async with SessionFactory() as session:
        claimed = await claim_waitlist_offer(session, first_in_line.id, buyers[1])
        assert claimed.buyer_id == buyers[1]
