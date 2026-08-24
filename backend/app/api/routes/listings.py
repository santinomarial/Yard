import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.listing import ListingCondition
from app.schemas.listing import ListingPage, ListingQuery, ListingRead
from app.services.listings import get_active_listing, search_listings

router = APIRouter()


@router.get("", response_model=ListingPage)
async def list_listings(
    query: str | None = Query(default=None, max_length=120),
    category: str | None = None,
    condition: ListingCondition | None = None,
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    free_only: bool = False,
    pickup_zone: str | None = None,
    sort: str = Query(default="newest", pattern="^(newest|price_asc|price_desc)$"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> ListingPage:
    filters = ListingQuery(
        query=query,
        category=category,
        condition=condition,
        min_price_cents=min_price_cents,
        max_price_cents=max_price_cents,
        free_only=free_only,
        pickup_zone=pickup_zone,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return await search_listings(session, filters)


@router.get("/{listing_id}", response_model=ListingRead)
async def listing_detail(
    listing_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ListingRead:
    listing = await get_active_listing(session, listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "listing_not_found", "message": "This listing is unavailable."},
        )
    return listing
