import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.category import Category


class ListingCondition(StrEnum):
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"


class ListingStatus(StrEnum):
    DRAFT = "draft"
    PENDING_MODERATION = "pending_moderation"
    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    REMOVED = "removed"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="ck_listings_nonnegative_price"),
        CheckConstraint(
            "(is_free = true AND price_cents = 0) OR (is_free = false AND price_cents > 0)",
            name="ck_listings_free_price_consistency",
        ),
        Index("ix_listings_status_published", "status", "published_at"),
        Index("ix_listings_category_status", "category_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), index=True)
    subcategory_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )
    price_cents: Mapped[int] = mapped_column(Integer)
    is_free: Mapped[bool] = mapped_column(default=False)
    condition: Mapped[ListingCondition] = mapped_column(
        Enum(ListingCondition, name="listing_condition", native_enum=False)
    )
    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus, name="listing_status", native_enum=False), index=True
    )
    pickup_zone: Mapped[str] = mapped_column(String(100))
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    save_count: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[Category] = relationship(foreign_keys=[category_id], lazy="joined")
    subcategory: Mapped[Category | None] = relationship(
        foreign_keys=[subcategory_id], lazy="joined"
    )
