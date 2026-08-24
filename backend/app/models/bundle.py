import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.listing import utc_now


class Bundle(Base):
    __tablename__ = "bundles"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(140))
    price_cents: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BundleItem(Base):
    __tablename__ = "bundle_items"
    __table_args__ = (UniqueConstraint("listing_id", name="uq_bundle_item_listing"),)
    bundle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bundles.id"), primary_key=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), primary_key=True)


class BundleReservation(Base):
    __tablename__ = "bundle_reservations"
    __table_args__ = (
        UniqueConstraint("buyer_id", "idempotency_key", name="uq_bundle_reservation_buyer_key"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bundle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bundles.id"), index=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(index=True)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
