import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import ReportReason, ReportSeverity, ReportStatus, ReportTarget


class ReportCreate(BaseModel):
    target_type: ReportTarget
    target_id: uuid.UUID
    reason: ReportReason
    details: str | None = Field(default=None, max_length=2_000)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reporter_id: uuid.UUID
    target_type: ReportTarget
    target_id: uuid.UUID
    reason: ReportReason
    severity: ReportSeverity
    details: str | None
    status: ReportStatus
    assigned_admin_id: uuid.UUID | None
    resolution: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminResolutionAction(StrEnum):
    DISMISS = "dismiss"
    REMOVE_LISTING = "remove_listing"
    WARN_USER = "warn_user"
    SUSPEND_USER = "suspend_user"


class AdminResolution(BaseModel):
    action: AdminResolutionAction
    notes: str | None = Field(default=None, max_length=2_000)


class AdminActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admin_id: uuid.UUID
    report_id: uuid.UUID | None
    action_type: str
    target_type: str
    target_id: uuid.UUID
    notes: str | None
    created_at: datetime


class AdminDashboard(BaseModel):
    open_reports: int
    reports_resolved_today: int
    active_listings: int
    new_users_today: int
    completed_exchanges: int
    moderation_backlog: int
