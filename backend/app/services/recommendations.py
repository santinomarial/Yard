import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer import BuyingIntent, SavedListing
from app.models.listing import Listing, ListingStatus


@dataclass(frozen=True)
class Recommendation:
    listing: Listing
    score: float
    reasons: list[str]


async def recommend_for_user(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 20
) -> list[Recommendation]:
    saved_categories = set(
        (
            await session.scalars(
                select(Listing.category_id)
                .join(SavedListing, SavedListing.listing_id == Listing.id)
                .where(SavedListing.user_id == user_id)
            )
        ).all()
    )
    intent_categories = set(
        (
            await session.scalars(
                select(BuyingIntent.category_id).where(
                    BuyingIntent.buyer_id == user_id,
                    BuyingIntent.is_active.is_(True),
                    BuyingIntent.category_id.is_not(None),
                )
            )
        ).all()
    )
    preferred_categories = saved_categories | intent_categories
    listings = (
        await session.scalars(
            select(Listing)
            .where(Listing.status == ListingStatus.ACTIVE, Listing.seller_id != user_id)
            .order_by(Listing.published_at.desc())
            .limit(300)
        )
    ).unique()
    now = datetime.now(UTC)
    ranked: list[Recommendation] = []
    for listing in listings:
        published = listing.published_at or listing.created_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        age_days = max(0.0, (now - published).total_seconds() / 86_400)
        freshness = math.exp(-age_days / 14)
        popularity = min(1.0, listing.save_count / 10)
        category_fit = 1.0 if listing.category_id in preferred_categories else 0.0
        score = 0.55 * category_fit + 0.30 * freshness + 0.15 * popularity
        reasons = []
        if category_fit:
            reasons.append("Matches categories you saved or requested")
        if freshness >= 0.7:
            reasons.append("Recently listed")
        if popularity >= 0.5:
            reasons.append("Frequently saved")
        if not reasons:
            reasons.append("Active near campus")
        ranked.append(Recommendation(listing, round(score, 4), reasons))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:limit]
