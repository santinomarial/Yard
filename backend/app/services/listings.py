import uuid
from urllib.parse import quote

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.category import Category
from app.models.listing import Listing, ListingStatus
from app.models.listing_image import ListingImage, ListingImageStatus
from app.schemas.listing import ListingPage, ListingQuery, ListingRead
from app.schemas.listing_image import ListingImageRead


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


def _apply_filters(
    statement: Select[tuple[Listing]], query: ListingQuery
) -> Select[tuple[Listing]]:
    statement = statement.where(Listing.status == ListingStatus.ACTIVE)
    if query.query:
        pattern = f"%{query.query.strip()}%"
        statement = statement.where(
            or_(Listing.title.ilike(pattern), Listing.description.ilike(pattern))
        )
    if query.category:
        statement = statement.join(Listing.category).where(Category.slug == query.category)
    if query.condition:
        statement = statement.where(Listing.condition == query.condition)
    if query.free_only:
        statement = statement.where(Listing.is_free.is_(True))
    if query.min_price_cents is not None:
        statement = statement.where(Listing.price_cents >= query.min_price_cents)
    if query.max_price_cents is not None:
        statement = statement.where(Listing.price_cents <= query.max_price_cents)
    if query.pickup_zone:
        statement = statement.where(Listing.pickup_zone == query.pickup_zone)
    return statement


async def search_listings(session: AsyncSession, query: ListingQuery) -> ListingPage:
    filtered = _apply_filters(select(Listing), query)
    count_statement = _apply_filters(select(Listing), query).with_only_columns(
        func.count(Listing.id), maintain_column_froms=True
    )
    total = int((await session.scalar(count_statement)) or 0)

    if query.sort == "price_asc":
        filtered = filtered.order_by(Listing.price_cents.asc(), Listing.published_at.desc())
    elif query.sort == "price_desc":
        filtered = filtered.order_by(Listing.price_cents.desc(), Listing.published_at.desc())
    else:
        filtered = filtered.order_by(Listing.published_at.desc())

    rows = await session.scalars(filtered.limit(query.limit).offset(query.offset))
    return ListingPage(
        items=[listing_read_model(item) for item in rows.unique().all()],
        total=total,
        limit=query.limit,
        offset=query.offset,
    )


async def get_active_listing(session: AsyncSession, listing_id: uuid.UUID) -> ListingRead | None:
    statement = select(Listing).where(
        Listing.id == listing_id, Listing.status == ListingStatus.ACTIVE
    )
    listing = await session.scalar(statement)
    return listing_read_model(listing) if listing else None
