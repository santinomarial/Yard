import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete

from app.core.database import SessionFactory
from app.models import Category, Listing, ListingCondition, ListingStatus
from app.schemas.listing import ListingQuery
from app.services.embeddings import write_listing_embedding
from app.services.listings import search_listings

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_pgvector_semantic_candidate_retrieves_screen_as_monitor() -> None:
    async with SessionFactory() as session, session.begin():
        await session.execute(
            delete(Listing).where(Listing.title == "Portable OLED Monitor")
        )
        category = Category(
            name=f"Semantic {uuid.uuid4().hex[:8]}",
            slug=f"semantic-{uuid.uuid4().hex}",
            symbol="display",
        )
        session.add(category)
        await session.flush()
        listing = Listing(
            seller_id=uuid.uuid4(),
            title="Portable OLED Monitor",
            description="A bright USB-C panel in excellent condition.",
            category=category,
            price_cents=7_500,
            is_free=False,
            condition=ListingCondition.GOOD,
            status=ListingStatus.ACTIVE,
            pickup_zone="Harvard Square",
            published_at=datetime.now(UTC),
        )
        session.add(listing)
        await session.flush()
        listing_id = listing.id
        await write_listing_embedding(session, listing)

    async with SessionFactory() as session:
        results = await search_listings(
            session,
            ListingQuery(query="second screen for coding", sort="recommended", limit=10),
        )

    assert listing_id in {item.id for item in results.items}
