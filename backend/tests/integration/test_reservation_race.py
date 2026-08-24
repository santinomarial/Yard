import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.database import SessionFactory
from app.models import (
    Bundle,
    BundleItem,
    Category,
    Listing,
    ListingCondition,
    ListingStatus,
    Reservation,
    User,
    WaitlistEntry,
    WaitlistStatus,
)
from app.services.bundles import reserve_bundle
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


async def test_bundle_and_individual_reservation_cannot_double_allocate() -> None:
    async with SessionFactory() as session, session.begin():
        category = Category(
            name=f"Bundle {uuid.uuid4().hex[:8]}",
            slug=f"bundle-{uuid.uuid4().hex}",
            symbol="shippingbox",
        )
        seller = User(display_name="Bundle Seller", email_verified_at=datetime.now(UTC))
        bundle_buyer = User(display_name="Bundle Buyer", email_verified_at=datetime.now(UTC))
        item_buyer = User(display_name="Item Buyer", email_verified_at=datetime.now(UTC))
        session.add_all([category, seller, bundle_buyer, item_buyer])
        await session.flush()
        listings = [
            Listing(
                seller_id=seller.id,
                title=f"Bundle item {index}",
                description="Atomic bundle race fixture.",
                category=category,
                price_cents=3_000,
                is_free=False,
                condition=ListingCondition.GOOD,
                status=ListingStatus.ACTIVE,
                pickup_zone="Harvard Square",
            )
            for index in range(2)
        ]
        session.add_all(listings)
        await session.flush()
        bundle = Bundle(id=uuid.uuid4(), seller_id=seller.id, title="Desk setup", price_cents=5_000)
        session.add(bundle)
        session.add_all(
            [BundleItem(bundle_id=bundle.id, listing_id=listing.id) for listing in listings]
        )
        await session.flush()
        bundle_id = bundle.id
        listing_ids = [listing.id for listing in listings]
        bundle_buyer_id = bundle_buyer.id
        item_buyer_id = item_buyer.id

    async def bundle_attempt() -> str:
        async with SessionFactory() as session:
            try:
                await reserve_bundle(
                    session, bundle_id, bundle_buyer_id, f"bundle-race-{uuid.uuid4()}"
                )
                return "bundle"
            except ReservationError:
                return "conflict"

    results = await asyncio.gather(
        bundle_attempt(), attempt(listing_ids[0], item_buyer_id, f"item-race-{uuid.uuid4()}")
    )
    assert sum(result in {"bundle"} or result.startswith("success") for result in results) == 1
    async with SessionFactory() as session:
        rows = list(
            (
                await session.scalars(
                    select(Reservation).where(Reservation.listing_id.in_(listing_ids))
                )
            ).all()
        )
        assert len(rows) in {1, 2}
        assert len({row.bundle_reservation_id is not None for row in rows}) == 1
