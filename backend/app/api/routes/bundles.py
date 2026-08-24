import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import CurrentUser
from app.models.bundle import Bundle, BundleItem
from app.models.listing import Listing, ListingStatus
from app.schemas.bundle import (
    BundleCreate,
    BundleRead,
    BundleReservationRead,
    BundleReserve,
)
from app.services.bundles import reserve_bundle
from app.services.reservations import ReservationError

router = APIRouter()


async def bundle_read(session: AsyncSession, bundle: Bundle) -> BundleRead:
    listing_ids = list(
        (
            await session.scalars(
                select(BundleItem.listing_id).where(BundleItem.bundle_id == bundle.id)
            )
        ).all()
    )
    return BundleRead(
        id=bundle.id,
        seller_id=bundle.seller_id,
        title=bundle.title,
        price_cents=bundle.price_cents,
        is_active=bundle.is_active,
        listing_ids=listing_ids,
    )


@router.post("", response_model=BundleRead, status_code=201)
async def create_bundle(
    payload: BundleCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BundleRead:
    unique_ids = set(payload.listing_ids)
    if len(unique_ids) != len(payload.listing_ids):
        raise HTTPException(status_code=422, detail="Duplicate listing")
    listings = list(
        (
            await session.scalars(
                select(Listing).where(Listing.id.in_(unique_ids)).with_for_update(of=Listing)
            )
        )
        .unique()
        .all()
    )
    if len(listings) != len(unique_ids) or any(
        listing.seller_id != user.id or listing.status != ListingStatus.ACTIVE
        for listing in listings
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "bundle_inventory_unavailable",
                "message": "Choose your active listings.",
            },
        )
    bundle = Bundle(
        id=uuid.uuid4(),
        seller_id=user.id,
        title=payload.title,
        price_cents=payload.price_cents,
    )
    session.add(bundle)
    session.add_all(
        [BundleItem(bundle_id=bundle.id, listing_id=listing.id) for listing in listings]
    )
    await session.commit()
    return await bundle_read(session, bundle)


@router.post("/{bundle_id}/reserve", response_model=BundleReservationRead)
async def reserve(
    bundle_id: uuid.UUID,
    payload: BundleReserve,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BundleReservationRead:
    try:
        reservation, _ = await reserve_bundle(session, bundle_id, user.id, payload.idempotency_key)
    except ReservationError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
                if error.code == "interaction_blocked"
                else status.HTTP_409_CONFLICT
            ),
            detail={"code": error.code, "message": str(error)},
        ) from None
    return BundleReservationRead.model_validate(reservation)
