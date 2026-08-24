from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models import Category, Listing, ListingCondition, ListingStatus, User
from app.models.listing_image import ListingImage, ListingImageStatus


async def seller_fixture(session: AsyncSession) -> tuple[User, Listing]:
    seller = User(
        display_name="Seller Manager",
        harvard_email="seller-manager@harvard.edu",
        email_verified_at=datetime.now(UTC),
    )
    category = await session.scalar(select(Category).where(Category.parent_id.is_(None)).limit(1))
    assert category is not None
    session.add(seller)
    await session.flush()
    listing = Listing(
        seller_id=seller.id,
        title="Managed lamp",
        description="An approved lamp with a safe operational edit.",
        category=category,
        price_cents=2500,
        is_free=False,
        condition=ListingCondition.GOOD,
        status=ListingStatus.ACTIVE,
        pickup_zone="Harvard Yard",
        published_at=datetime.now(UTC),
    )
    session.add(listing)
    await session.flush()
    session.add(
        ListingImage(
            listing_id=listing.id,
            storage_key=f"listings/{listing.id}/approved.jpg",
            content_type="image/jpeg",
            byte_size=128,
            status=ListingImageStatus.APPROVED,
        )
    )
    await session.commit()
    return seller, listing


async def test_seller_can_edit_archive_and_relist_owned_listing(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    seller, listing = await seller_fixture(seeded_session)
    headers = {"Authorization": f"Bearer {create_access_token(seller.id)}"}

    updated = await client.patch(
        f"/api/v1/listings/{listing.id}",
        json={
            "price_cents": 0,
            "is_free": True,
            "condition": "fair",
            "pickup_zone": "Science Center",
        },
        headers=headers,
    )
    archived = await client.post(f"/api/v1/listings/{listing.id}/archive", headers=headers)
    relisted = await client.post(f"/api/v1/listings/{listing.id}/relist", headers=headers)

    assert updated.status_code == 200
    assert updated.json()["is_free"] is True
    assert updated.json()["pickup_zone"] == "Science Center"
    assert archived.json()["status"] == "archived"
    assert relisted.status_code == 200
    assert relisted.json()["status"] == "active"


async def test_non_owner_cannot_manage_listing(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    _, listing = await seller_fixture(seeded_session)
    stranger = User(
        display_name="Not Owner",
        harvard_email="not-owner@harvard.edu",
        email_verified_at=datetime.now(UTC),
    )
    seeded_session.add(stranger)
    await seeded_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(stranger.id)}"}

    response = await client.post(f"/api/v1/listings/{listing.id}/archive", headers=headers)

    assert response.status_code == 404


async def test_reserved_listing_cannot_be_archived(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    seller, listing = await seller_fixture(seeded_session)
    listing.status = ListingStatus.RESERVED
    await seeded_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(seller.id)}"}

    response = await client.post(f"/api/v1/listings/{listing.id}/archive", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "listing_unavailable_locked"
