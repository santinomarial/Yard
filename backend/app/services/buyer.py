from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer import BuyingIntent, ListingMatch
from app.models.listing import Listing, ListingStatus
from app.services.matching import IntentFeatures, score_match

MATCH_THRESHOLD = 0.55


def intent_features(intent: BuyingIntent) -> IntentFeatures:
    return IntentFeatures(
        query=intent.query,
        category_id=intent.category_id,
        maximum_price_cents=intent.maximum_price_cents,
        minimum_condition=intent.minimum_condition,
        pickup_zone=intent.pickup_zone,
    )


async def match_intent(session: AsyncSession, intent: BuyingIntent) -> list[ListingMatch]:
    listings = await session.scalars(select(Listing).where(Listing.status == ListingStatus.ACTIVE))
    matches: list[ListingMatch] = []
    for listing in listings.unique().all():
        score = score_match(intent_features(intent), listing)
        if score.total < MATCH_THRESHOLD:
            continue
        match = ListingMatch(
            intent_id=intent.id,
            listing_id=listing.id,
            score=score.total,
            score_components=score.components,
        )
        session.add(match)
        matches.append(match)
    return matches


async def match_listing(session: AsyncSession, listing: Listing) -> int:
    intents = await session.scalars(select(BuyingIntent).where(BuyingIntent.is_active.is_(True)))
    created = 0
    for intent in intents:
        score = score_match(intent_features(intent), listing)
        if score.total < MATCH_THRESHOLD:
            continue
        existing = await session.scalar(
            select(ListingMatch.id).where(
                ListingMatch.intent_id == intent.id, ListingMatch.listing_id == listing.id
            )
        )
        if existing is None:
            session.add(
                ListingMatch(
                    intent_id=intent.id,
                    listing_id=listing.id,
                    score=score.total,
                    score_components=score.components,
                )
            )
            created += 1
    return created
