import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.core.security import CurrentUser
from app.models.category import Category
from app.models.listing import Listing, ListingCondition, ListingStatus
from app.models.listing_image import ListingImage, ListingImageStatus
from app.models.marketplace_event import ListingEvent, ModerationResult
from app.schemas.listing import ListingDraftCreate, ListingPage, ListingQuery, ListingRead
from app.schemas.listing_image import (
    ListingImageRead,
    ListingImageUploadRead,
    ListingImageUploadRequest,
)
from app.services.analytics import record_event
from app.services.buyer import match_listing
from app.services.embeddings import write_listing_embedding
from app.services.image_moderation import (
    ImageModerationProvider,
    get_image_moderation_provider,
)
from app.services.listing_lifecycle import InvalidListingTransition, transition_listing
from app.services.listings import (
    get_active_listing,
    image_read_model,
    listing_read_model,
    search_listings,
)
from app.services.moderation import DeterministicDevelopmentModeration
from app.services.object_storage import ObjectStorage, get_object_storage

router = APIRouter()

Storage = Annotated[ObjectStorage, Depends(get_object_storage)]
ImageModerator = Annotated[ImageModerationProvider, Depends(get_image_moderation_provider)]

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/heif": "heif",
    "image/webp": "webp",
}


def detected_image_type(prefix: bytes) -> str | None:
    if prefix.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP":
        return "image/webp"
    if prefix[4:8] == b"ftyp":
        brand = prefix[8:12]
        if brand in {b"heic", b"heix", b"hevc", b"hevx"}:
            return "image/heic"
        if brand in {b"mif1", b"msf1", b"heif"}:
            return "image/heif"
    return None


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
        images=[],
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
    record_event(
        session,
        "listing_created",
        user_id=user.id,
        entity_type="listing",
        entity_id=listing.id,
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
    image_statuses = list(
        (
            await session.scalars(
                select(ListingImage.status).where(ListingImage.listing_id == listing.id)
            )
        ).all()
    )
    if (
        ListingImageStatus.PENDING_UPLOAD in image_statuses
        or ListingImageStatus.PENDING_MODERATION in image_statuses
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "image_moderation_pending",
                "message": "Wait for image checks to finish before publishing.",
            },
        )
    if ListingImageStatus.APPROVED not in image_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "listing_image_required",
                "message": "Add at least one approved item photo before publishing.",
            },
        )
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
    if decision.approved:
        await write_listing_embedding(session, listing)
        await match_listing(session, listing)
    await session.commit()
    return listing_read_model(listing)


async def owned_draft(
    session: AsyncSession, listing_id: uuid.UUID, seller_id: uuid.UUID
) -> Listing:
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id, Listing.seller_id == seller_id)
        .with_for_update(of=Listing)
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Not found")
    if listing.status != ListingStatus.DRAFT:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "listing_images_locked",
                "message": "Photos can only be changed while a listing is a draft.",
            },
        )
    return listing


@router.post("/{listing_id}/images/uploads", response_model=ListingImageUploadRead, status_code=201)
async def create_image_upload(
    listing_id: uuid.UUID,
    payload: ListingImageUploadRequest,
    user: CurrentUser,
    storage: Storage,
    session: AsyncSession = Depends(get_session),
) -> ListingImageUploadRead:
    require_verified(user)
    await owned_draft(session, listing_id, user.id)
    extension = ALLOWED_IMAGE_TYPES.get(payload.content_type.lower())
    if extension is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unsupported_image_type",
                "message": "Upload a JPEG, PNG, HEIC, HEIF, or WebP image.",
            },
        )
    count = int(
        await session.scalar(
            select(func.count())
            .select_from(ListingImage)
            .where(ListingImage.listing_id == listing_id)
        )
        or 0
    )
    if count >= 8:
        raise HTTPException(
            status_code=409,
            detail={"code": "image_limit_reached", "message": "A listing supports up to 8 photos."},
        )
    image_id = uuid.uuid4()
    storage_key = f"listings/{listing_id}/{image_id}.{extension}"
    image = ListingImage(
        id=image_id,
        listing_id=listing_id,
        storage_key=storage_key,
        content_type=payload.content_type.lower(),
        byte_size=payload.byte_size,
        sort_order=payload.sort_order,
        status=ListingImageStatus.PENDING_UPLOAD,
    )
    session.add(image)
    await session.commit()
    upload = storage.presign_upload(storage_key, image.content_type)
    return ListingImageUploadRead(
        image=image_read_model(image),
        upload_url=upload.url,
        required_headers=upload.headers,
        expires_in_seconds=upload.expires_in_seconds,
    )


@router.post("/{listing_id}/images/{image_id}/complete", response_model=ListingImageRead)
async def complete_image_upload(
    listing_id: uuid.UUID,
    image_id: uuid.UUID,
    user: CurrentUser,
    storage: Storage,
    moderator: ImageModerator,
    session: AsyncSession = Depends(get_session),
) -> ListingImageRead:
    await owned_draft(session, listing_id, user.id)
    image = await session.scalar(
        select(ListingImage).where(
            ListingImage.id == image_id, ListingImage.listing_id == listing_id
        )
    )
    if image is None:
        raise HTTPException(status_code=404, detail="Not found")
    if image.status in {ListingImageStatus.APPROVED, ListingImageStatus.REJECTED}:
        return image_read_model(image)
    try:
        stored = await storage.head(image.storage_key)
        prefix = await storage.read_prefix(image.storage_key)
    except Exception:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "image_upload_missing",
                "message": "Finish the photo upload before marking it complete.",
            },
        ) from None
    if (
        stored.byte_size != image.byte_size
        or (stored.content_type and stored.content_type.lower() != image.content_type)
        or detected_image_type(prefix) != image.content_type
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "image_metadata_mismatch",
                "message": "The uploaded photo does not match its declared metadata.",
            },
        )
    image.status = ListingImageStatus.PENDING_MODERATION
    image.uploaded_at = datetime.now(UTC)
    await session.commit()
    try:
        decision = await moderator.moderate(image.storage_key)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "image_moderation_unavailable",
                "message": "Photo checks are temporarily unavailable. Try again shortly.",
            },
        ) from None
    image.status = ListingImageStatus.APPROVED if decision.approved else ListingImageStatus.REJECTED
    image.moderation_provider = decision.provider
    image.moderation_reasons = decision.reasons
    image.moderated_at = datetime.now(UTC)
    await session.commit()
    return image_read_model(image)


@router.delete("/{listing_id}/images/{image_id}", status_code=204)
async def delete_image(
    listing_id: uuid.UUID,
    image_id: uuid.UUID,
    user: CurrentUser,
    storage: Storage,
    session: AsyncSession = Depends(get_session),
) -> None:
    await owned_draft(session, listing_id, user.id)
    image = await session.scalar(
        select(ListingImage).where(
            ListingImage.id == image_id, ListingImage.listing_id == listing_id
        )
    )
    if image is None:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        await storage.delete(image.storage_key)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "image_storage_unavailable",
                "message": "The photo could not be removed. Try again shortly.",
            },
        ) from None
    await session.delete(image)
    await session.commit()


@router.get("", response_model=ListingPage)
async def list_listings(
    query: str | None = Query(default=None, max_length=120),
    category: str | None = None,
    condition: ListingCondition | None = None,
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    free_only: bool = False,
    pickup_zone: str | None = None,
    sort: str = Query(default="recommended", pattern="^(recommended|newest|price_asc|price_desc)$"),
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
    page = await search_listings(session, filters)
    if query:
        record_event(
            session,
            "search_performed",
            properties={"query": query.strip(), "result_count": page.total},
        )
        await session.commit()
    return page


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
    record_event(
        session,
        "listing_viewed",
        entity_type="listing",
        entity_id=listing_id,
    )
    await session.commit()
    return listing
