import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import Select, case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.category import Category
from app.models.listing import Listing, ListingStatus
from app.models.listing_image import ListingImage, ListingImageStatus
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User
from app.schemas.listing import ListingPage, ListingQuery, ListingRead, SellerTrustRead
from app.schemas.listing_image import ListingImageRead
from app.services.embeddings import local_embedding, vector_literal


def image_url(storage_key: str) -> str:
    return f"{get_settings().asset_base_url.rstrip('/')}/{quote(storage_key)}"


def image_read_model(image: ListingImage) -> ListingImageRead:
    return ListingImageRead(
        id=image.id,
        content_type=image.content_type,
        byte_size=image.byte_size,
        sort_order=image.sort_order,
        status=image.status,
        url=image_url(image.storage_key) if image.status == ListingImageStatus.APPROVED else None,
        moderation_reasons=image.moderation_reasons,
        uploaded_at=image.uploaded_at,
    )


def listing_read_model(listing: Listing) -> ListingRead:
    images = [
        image_read_model(image)
        for image in listing.images
        if image.status == ListingImageStatus.APPROVED
    ]
    return ListingRead(
        id=listing.id,
        seller_id=listing.seller_id,
        title=listing.title,
        description=listing.description,
        category_id=listing.category_id,
        subcategory_id=listing.subcategory_id,
        category_name=listing.category.name,
        subcategory_name=listing.subcategory.name if listing.subcategory else None,
        price_cents=listing.price_cents,
        is_free=listing.is_free,
        condition=listing.condition,
        status=listing.status,
        pickup_zone=listing.pickup_zone,
        image_url=images[0].url if images else listing.image_url,
        images=images,
        published_at=listing.published_at,
        view_count=listing.view_count,
        save_count=listing.save_count,
    )


async def attach_seller_trust(
    session: AsyncSession, listings: list[ListingRead]
) -> list[ListingRead]:
    seller_ids = {listing.seller_id for listing in listings}
    if not seller_ids:
        return listings
    users = list(
        (
            await session.scalars(
                select(User).where(
                    User.id.in_(seller_ids),
                    User.deleted_at.is_(None),
                    User.suspended_at.is_(None),
                )
            )
        ).all()
    )
    completed_rows = await session.execute(
        select(Reservation.seller_id, func.count(Reservation.id))
        .where(
            Reservation.seller_id.in_(seller_ids),
            Reservation.status == ReservationStatus.COMPLETED,
        )
        .group_by(Reservation.seller_id)
    )
    completed: dict[uuid.UUID, int] = {
        seller_id: int(count) for seller_id, count in completed_rows.all()
    }
    users_by_id = {user.id: user for user in users}
    for listing in listings:
        seller = users_by_id.get(listing.seller_id)
        if seller:
            listing.seller = SellerTrustRead(
                display_name=seller.display_name,
                harvard_email_verified=seller.email_verified_at is not None,
                member_since=seller.created_at,
                completed_exchanges=int(completed.get(seller.id, 0)),
            )
    return listings


def _apply_filters(
    statement: Select[tuple[Listing]], query: ListingQuery, *, include_query_text: bool = True
) -> Select[tuple[Listing]]:
    statement = statement.where(Listing.status == ListingStatus.ACTIVE)
    if query.query and include_query_text:
        pattern = f"%{query.query.strip()}%"
        statement = statement.where(
            or_(Listing.title.ilike(pattern), Listing.description.ilike(pattern))
        )
    if query.category:
        statement = statement.join(Listing.category).where(Category.slug == query.category)
    if query.subcategory:
        statement = statement.where(Listing.subcategory.has(Category.slug == query.subcategory))
    if query.condition:
        statement = statement.where(Listing.condition == query.condition)
    if query.free_only:
        statement = statement.where(Listing.is_free.is_(True))
    if query.min_price_cents is not None:
        statement = statement.where(Listing.price_cents >= query.min_price_cents)
    if query.max_price_cents is not None:
        statement = statement.where(Listing.price_cents <= query.max_price_cents)
    if query.pickup_zone and query.sort != "closest":
        statement = statement.where(Listing.pickup_zone == query.pickup_zone)
    if query.max_age_days is not None:
        published_after = datetime.now(UTC) - timedelta(days=query.max_age_days)
        statement = statement.where(Listing.published_at >= published_after)
    return statement


async def hybrid_candidate_ids(session: AsyncSession, query: str) -> list[uuid.UUID]:
    embedding = vector_literal(local_embedding(query))
    rows = await session.execute(
        text(
            """
            WITH lexical AS (
                SELECT id,
                       ts_rank(search_document, websearch_to_tsquery('english', :query)) AS score
                FROM listings
                WHERE status = 'ACTIVE'
                  AND search_document @@ websearch_to_tsquery('english', :query)
                ORDER BY score DESC
                LIMIT 200
            ),
            semantic AS (
                SELECT id, 1 - (embedding <=> CAST(:embedding AS vector)) AS score
                FROM listings
                WHERE status = 'ACTIVE' AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT 200
            ),
            candidates AS (
                SELECT id, score * 0.55 AS score FROM lexical
                UNION ALL
                SELECT id, score * 0.45 AS score FROM semantic
            )
            SELECT id
            FROM candidates
            GROUP BY id
            ORDER BY SUM(score) DESC
            LIMIT 300
            """
        ),
        {"query": query, "embedding": embedding},
    )
    return [row[0] for row in rows]


async def search_listings(session: AsyncSession, query: ListingQuery) -> ListingPage:
    ranked_ids: list[uuid.UUID] | None = None
    is_postgres = session.bind is not None and session.bind.dialect.name == "postgresql"
    if query.query and is_postgres:
        ranked_ids = await hybrid_candidate_ids(session, query.query.strip())
        if not ranked_ids:
            return ListingPage(items=[], total=0, limit=query.limit, offset=query.offset)

    include_query_text = ranked_ids is None
    filtered = _apply_filters(select(Listing), query, include_query_text=include_query_text)
    count_source = _apply_filters(select(Listing), query, include_query_text=include_query_text)
    if ranked_ids is not None:
        filtered = filtered.where(Listing.id.in_(ranked_ids))
        count_source = count_source.where(Listing.id.in_(ranked_ids))
    count_statement = count_source.with_only_columns(
        func.count(Listing.id), maintain_column_froms=True
    )
    total = int((await session.scalar(count_statement)) or 0)

    if query.sort == "price_asc":
        filtered = filtered.order_by(Listing.price_cents.asc(), Listing.published_at.desc())
    elif query.sort == "price_desc":
        filtered = filtered.order_by(Listing.price_cents.desc(), Listing.published_at.desc())
    elif query.sort == "closest" and query.pickup_zone:
        filtered = filtered.order_by(
            case((Listing.pickup_zone == query.pickup_zone, 0), else_=1),
            Listing.published_at.desc(),
        )
    elif ranked_ids is not None and query.sort == "recommended":
        rank = {listing_id: index for index, listing_id in enumerate(ranked_ids)}
        filtered = filtered.order_by(case(rank, value=Listing.id, else_=len(rank)))
    else:
        filtered = filtered.order_by(Listing.published_at.desc())

    rows = await session.scalars(filtered.limit(query.limit).offset(query.offset))
    items = [listing_read_model(item) for item in rows.unique().all()]
    await attach_seller_trust(session, items)
    return ListingPage(
        items=items,
        total=total,
        limit=query.limit,
        offset=query.offset,
    )


async def get_active_listing(session: AsyncSession, listing_id: uuid.UUID) -> ListingRead | None:
    statement = select(Listing).where(
        Listing.id == listing_id, Listing.status == ListingStatus.ACTIVE
    )
    listing = await session.scalar(statement)
    if listing is None:
        return None
    result = listing_read_model(listing)
    await attach_seller_trust(session, [result])
    return result
