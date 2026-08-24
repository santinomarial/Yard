import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import CurrentUser
from app.models.buyer import BuyingIntent, ListingMatch, SavedListing
from app.models.listing import Listing, ListingStatus
from app.schemas.buyer import (
    BuyingIntentCreate,
    BuyingIntentRead,
    ListingMatchRead,
    RecommendationRead,
)
from app.schemas.listing import ListingRead
from app.services.analytics import record_event
from app.services.buyer import match_intent
from app.services.listings import attach_seller_trust, listing_read_model
from app.services.recommendations import recommend_for_user

router = APIRouter()


@router.get("/saved", response_model=list[ListingRead])
async def saved_listings(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[ListingRead]:
    rows = await session.scalars(
        select(Listing)
        .join(SavedListing, SavedListing.listing_id == Listing.id)
        .where(SavedListing.user_id == user.id, Listing.status == ListingStatus.ACTIVE)
        .order_by(SavedListing.created_at.desc())
    )
    listings = [listing_read_model(item) for item in rows.unique().all()]
    return await attach_seller_trust(session, listings)


@router.put("/saved/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def save_listing(
    listing_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Response:
    listing = await session.get(Listing, listing_id)
    if listing is None or listing.status != ListingStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Not found")
    exists = await session.get(SavedListing, (user.id, listing_id))
    if exists is None:
        session.add(SavedListing(user_id=user.id, listing_id=listing_id))
        listing.save_count += 1
        record_event(
            session,
            "listing_saved",
            user_id=user.id,
            entity_type="listing",
            entity_id=listing.id,
        )
        await session.commit()
    return Response(status_code=204)


@router.delete("/saved/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_listing(
    listing_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Response:
    result = await session.execute(
        delete(SavedListing).where(
            SavedListing.user_id == user.id, SavedListing.listing_id == listing_id
        )
    )
    if result.rowcount:  # type: ignore[attr-defined]
        listing = await session.get(Listing, listing_id)
        if listing:
            listing.save_count = max(0, listing.save_count - 1)
    await session.commit()
    return Response(status_code=204)


@router.post("/intents", response_model=BuyingIntentRead, status_code=201)
async def create_intent(
    payload: BuyingIntentCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BuyingIntent:
    intent = BuyingIntent(buyer_id=user.id, **payload.model_dump())
    session.add(intent)
    await session.flush()
    await match_intent(session, intent)
    record_event(
        session,
        "buying_intent_created",
        user_id=user.id,
        entity_type="buying_intent",
        entity_id=intent.id,
    )
    await session.commit()
    return intent


@router.get("/intents", response_model=list[BuyingIntentRead])
async def intents(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[BuyingIntent]:
    rows = await session.scalars(
        select(BuyingIntent)
        .where(BuyingIntent.buyer_id == user.id)
        .order_by(BuyingIntent.created_at.desc())
    )
    return list(rows.all())


@router.get("/intents/{intent_id}/matches", response_model=list[ListingMatchRead])
async def intent_matches(
    intent_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[ListingMatchRead]:
    intent = await session.scalar(
        select(BuyingIntent).where(BuyingIntent.id == intent_id, BuyingIntent.buyer_id == user.id)
    )
    if intent is None:
        raise HTTPException(status_code=404, detail="Not found")
    pairs = (
        await session.execute(
            select(ListingMatch, Listing)
            .join(Listing, Listing.id == ListingMatch.listing_id)
            .where(ListingMatch.intent_id == intent.id, Listing.status == ListingStatus.ACTIVE)
            .order_by(ListingMatch.score.desc())
        )
    ).all()
    results = [
        ListingMatchRead(
            id=match.id,
            score=match.score,
            score_components=match.score_components,
            listing=listing_read_model(listing),
        )
        for match, listing in pairs
    ]
    await attach_seller_trust(session, [item.listing for item in results])
    return results


@router.get("/recommendations", response_model=list[RecommendationRead])
async def recommendations(
    user: CurrentUser,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[RecommendationRead]:
    items = await recommend_for_user(session, user.id, max(1, min(limit, 50)))
    results = [
        RecommendationRead(
            score=item.score,
            reasons=item.reasons,
            listing=listing_read_model(item.listing),
        )
        for item in items
    ]
    await attach_seller_trust(session, [item.listing for item in results])
    return results
