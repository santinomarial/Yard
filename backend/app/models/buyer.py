import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.listing import ListingCondition, utc_now


class SavedListing(Base):
    __tablename__ = "saved_listings"
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BuyingIntent(Base):
    __tablename__ = "buying_intents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    buyer_id: Mapped[uuid.UUID] = mapped_column(index=True)
    query: Mapped[str] = mapped_column(String(140))
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    maximum_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_condition: Mapped[ListingCondition | None] = mapped_column(
        Enum(ListingCondition, name="intent_condition", native_enum=False), nullable=True
    )
    pickup_zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ListingMatch(Base):
    __tablename__ = "listing_matches"
    __table_args__ = (UniqueConstraint("intent_id", "listing_id", name="uq_match_intent_listing"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    intent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("buying_intents.id"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    score_components: Mapped[dict[str, float]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
