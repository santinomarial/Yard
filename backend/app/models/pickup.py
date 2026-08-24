import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.listing import utc_now


class PickupStatus(StrEnum):
    PROPOSED = "proposed"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ArrivalStatus(StrEnum):
    PLANNED = "planned"
    ON_THE_WAY = "on_the_way"
    ARRIVED = "arrived"


class PickupSession(Base):
    __tablename__ = "pickup_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id"), unique=True, index=True
    )
    proposed_by: Mapped[uuid.UUID] = mapped_column(index=True)
    meeting_zone: Mapped[str] = mapped_column(String(100))
    proposed_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[PickupStatus] = mapped_column(
        Enum(PickupStatus, name="pickup_status", native_enum=False), index=True
    )
    buyer_arrival: Mapped[ArrivalStatus] = mapped_column(
        Enum(ArrivalStatus, name="arrival_status", native_enum=False),
        default=ArrivalStatus.PLANNED,
    )
    seller_arrival: Mapped[ArrivalStatus] = mapped_column(
        Enum(ArrivalStatus, name="arrival_status", native_enum=False),
        default=ArrivalStatus.PLANNED,
    )
    buyer_eta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seller_eta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    buyer_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seller_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
