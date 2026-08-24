import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models import (
    Listing,
    ListingStatus,
    PickupStatus,
    Reservation,
    ReservationStatus,
    User,
)


def headers_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def pickup_fixture(
    session: AsyncSession,
) -> tuple[Listing, Reservation, User, User, User]:
    listing = await session.scalar(
        select(Listing).where(Listing.status == ListingStatus.ACTIVE).limit(1)
    )
    assert listing is not None
    listing.status = ListingStatus.RESERVED
    listing.reserved_at = datetime.now(UTC)
    seller = User(id=listing.seller_id, display_name="Pickup Seller")
    buyer = User(display_name="Pickup Buyer")
    outsider = User(display_name="Pickup Outsider")
    session.add_all([seller, buyer, outsider])
    await session.flush()
    reservation = Reservation(
        listing_id=listing.id,
        buyer_id=buyer.id,
        seller_id=seller.id,
        status=ReservationStatus.ACTIVE,
        idempotency_key=f"pickup-{uuid.uuid4()}",
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    session.add(reservation)
    await session.commit()
    return listing, reservation, seller, buyer, outsider


async def test_pickup_requires_both_parties_to_complete_exchange(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    listing, reservation, seller, buyer, outsider = await pickup_fixture(seeded_session)
    listing_id = listing.id
    reservation_id = reservation.id
    seller_headers = headers_for(seller)
    buyer_headers = headers_for(buyer)
    outsider_headers = headers_for(outsider)
    proposed_for = datetime.now(UTC) + timedelta(hours=1)
    proposed = await client.post(
        "/api/v1/pickups",
        json={
            "reservation_id": str(reservation_id),
            "meeting_zone": "Smith Campus Center area",
            "proposed_for": proposed_for.isoformat(),
        },
        headers=buyer_headers,
    )
    assert proposed.status_code == 201
    assert proposed.json()["status"] == "proposed"

    hidden = await client.get(f"/api/v1/pickups/{reservation_id}", headers=outsider_headers)
    assert hidden.status_code == 404
    self_accept = await client.post(
        f"/api/v1/pickups/{reservation_id}/accept", headers=buyer_headers
    )
    assert self_accept.status_code == 409

    accepted = await client.post(f"/api/v1/pickups/{reservation_id}/accept", headers=seller_headers)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "scheduled"
    assert accepted.json()["accepted_at"] is not None

    presence = await client.patch(
        f"/api/v1/pickups/{reservation_id}/presence",
        json={"status": "on_the_way", "eta_minutes": 6},
        headers=buyer_headers,
    )
    assert presence.status_code == 200
    assert presence.json()["buyer_eta_minutes"] == 6

    first_confirmation = await client.post(
        f"/api/v1/pickups/{reservation_id}/complete", headers=buyer_headers
    )
    assert first_confirmation.status_code == 200
    assert first_confirmation.json()["status"] == "scheduled"
    completed = await client.post(
        f"/api/v1/pickups/{reservation_id}/complete", headers=seller_headers
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    reservation = await seeded_session.get(Reservation, reservation_id)
    listing = await seeded_session.get(Listing, listing_id)
    assert reservation is not None and listing is not None
    assert reservation.status == ReservationStatus.COMPLETED
    assert listing.status == ListingStatus.SOLD


async def test_pickup_cancellation_releases_listing(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    listing, reservation, seller, buyer, _ = await pickup_fixture(seeded_session)
    listing_id = listing.id
    reservation_id = reservation.id
    seller_headers = headers_for(seller)
    buyer_headers = headers_for(buyer)
    proposed = await client.post(
        "/api/v1/pickups",
        json={
            "reservation_id": str(reservation_id),
            "meeting_zone": "Harvard Square",
            "proposed_for": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        },
        headers=seller_headers,
    )
    assert proposed.status_code == 201
    assert (
        await client.post(f"/api/v1/pickups/{reservation_id}/accept", headers=buyer_headers)
    ).status_code == 200

    cancelled = await client.post(f"/api/v1/pickups/{reservation_id}/cancel", headers=buyer_headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == PickupStatus.CANCELLED.value
    reservation = await seeded_session.get(Reservation, reservation_id)
    listing = await seeded_session.get(Listing, listing_id)
    assert reservation is not None and listing is not None
    assert reservation.status == ReservationStatus.CANCELLED
    assert listing.status == ListingStatus.ACTIVE


async def test_reservations_are_visible_only_to_participants(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    _, reservation, seller, buyer, outsider = await pickup_fixture(seeded_session)
    reservation_id = reservation.id
    buyer_headers = headers_for(buyer)
    seller_headers = headers_for(seller)
    outsider_headers = headers_for(outsider)

    buyer_rows = await client.get("/api/v1/reservations/mine", headers=buyer_headers)
    seller_rows = await client.get("/api/v1/reservations/mine", headers=seller_headers)
    outsider_rows = await client.get("/api/v1/reservations/mine", headers=outsider_headers)

    assert buyer_rows.status_code == 200
    assert seller_rows.status_code == 200
    assert [row["id"] for row in buyer_rows.json()] == [str(reservation_id)]
    assert [row["id"] for row in seller_rows.json()] == [str(reservation_id)]
    assert outsider_rows.json() == []
