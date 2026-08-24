import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.listing import utc_now


class ReportTarget(StrEnum):
    LISTING = "listing"
    USER = "user"
    MESSAGE = "message"


class ReportReason(StrEnum):
    PROHIBITED_ITEM = "prohibited_item"
    SCAM_FRAUD = "scam_fraud"
    HARASSMENT = "harassment"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    COUNTERFEIT_STOLEN = "counterfeit_stolen"
    SPAM = "spam"
    OTHER = "other"


class ReportStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ReportSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN listing_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN reported_user_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN message_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_report_exactly_one_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    target_type: Mapped[ReportTarget] = mapped_column(
        Enum(ReportTarget, name="report_target", native_enum=False), index=True
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("listings.id"), nullable=True, index=True
    )
    reported_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True, index=True
    )
    reason: Mapped[ReportReason] = mapped_column(
        Enum(ReportReason, name="report_reason", native_enum=False), index=True
    )
    severity: Mapped[ReportSeverity] = mapped_column(
        Enum(ReportSeverity, name="report_severity", native_enum=False), index=True
    )
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status", native_enum=False), index=True
    )
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    resolution: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    @property
    def target_id(self) -> uuid.UUID:
        target_id = self.listing_id or self.reported_user_id or self.message_id
        if target_id is None:
            raise ValueError("Report has no target")
        return target_id


class AdminAction(Base):
    __tablename__ = "admin_actions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reports.id"), nullable=True, index=True
    )
    action_type: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[uuid.UUID] = mapped_column(index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
