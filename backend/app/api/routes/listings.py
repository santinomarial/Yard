import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.core.security import CurrentUser
from app.models.category import Category
from app.models.listing import Listing, ListingCondition, ListingStatus
from app.models.marketplace_event import ListingEvent, ModerationResult
from app.schemas.listing import ListingDraftCreate, ListingPage, ListingQuery, ListingRead
from app.services.listing_lifecycle import InvalidListingTransition, transition_listing
from app.services.listings import get_active_listing, listing_read_model, search_listings
from app.services.moderation import DeterministicDevelopmentModeration

router = APIRouter()


def require_verified(user: CurrentUser) -> None:
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "harvard_email_required",
                "message": "Verify a Harvard email before using the marketplace.",
            },
        )


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
async def create_listing_draft(
    payload: ListingDraftCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ListingRead:
    require_verified(user)
    if payload.is_free != (payload.price_cents == 0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_price", "message": "Free listings must have a zero price."},
        )
    category = await session.get(Category, payload.category_id)
    subcategory = (
        await session.get(Category, payload.subcategory_id) if payload.subcategory_id else None
    )
    if category is None or category.parent_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_category", "message": "Choose an active category."},
        )
    if subcategory and subcategory.parent_id != category.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_subcategory", "message": "Choose a matching subcategory."},
        )
    listing = Listing(
        seller_id=user.id,
        title=payload.title,
        description=payload.description,
        category=category,
        subcategory=subcategory,
        price_cents=payload.price_cents,
        is_free=payload.is_free,
        condition=payload.condition,
        status=ListingStatus.DRAFT,
        pickup_zone=payload.pickup_zone,
    )
    session.add(listing)
    await session.flush()
    session.add(
        ListingEvent(
            listing_id=listing.id,
            actor_id=user.id,
            event_type="ListingCreated",
            to_status=ListingStatus.DRAFT.value,
        )
    )
    await session.commit()
    return listing_read_model(listing)


@router.get("/mine", response_model=list[ListingRead])
async def my_listings(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[ListingRead]:
    statement = (
        select(Listing)
        .where(Listing.seller_id == user.id)
        .options(selectinload(Listing.category), selectinload(Listing.subcategory))
        .order_by(Listing.updated_at.desc())
    )
    items = await session.scalars(statement)
    return [listing_read_model(item) for item in items.unique().all()]


@router.post("/{listing_id}/submit", response_model=ListingRead)
async def submit_listing(
    listing_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ListingRead:
    require_verified(user)
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id, Listing.seller_id == user.id)
        .with_for_update()
    )
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        session.add(
            transition_listing(
                listing,
                ListingStatus.PENDING_MODERATION,
                user.id,
                "ListingSubmittedForModeration",
            )
        )
    except InvalidListingTransition as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_listing_state", "message": str(error)},
        ) from None
    decision = await DeterministicDevelopmentModeration().moderate(listing)
    session.add(
        ModerationResult(
            listing_id=listing.id,
            provider=decision.provider,
            outcome="approved" if decision.approved else "rejected",
            reasons=decision.reasons,
        )
    )
    target = ListingStatus.ACTIVE if decision.approved else ListingStatus.REJECTED
    session.add(
        transition_listing(
            listing,
            target,
            user.id,
            "ListingPublished" if decision.approved else "ListingRejected",
            {"provider": decision.provider},
        )
    )
    await session.commit()
    return listing_read_model(listing)


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
