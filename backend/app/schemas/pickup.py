import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.pickup import ArrivalStatus, PickupStatus


class PickupProposal(BaseModel):
    reservation_id: uuid.UUID
    meeting_zone: str = Field(min_length=2, max_length=100)
    proposed_for: datetime


class PickupPresenceUpdate(BaseModel):
    status: ArrivalStatus
    eta_minutes: int | None = Field(default=None, ge=0, le=120)


class PickupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_id: uuid.UUID
    proposed_by: uuid.UUID
    meeting_zone: str
    proposed_for: datetime
    status: PickupStatus
    buyer_arrival: ArrivalStatus
    seller_arrival: ArrivalStatus
    buyer_eta_minutes: int | None
    seller_eta_minutes: int | None
    accepted_at: datetime | None
    buyer_confirmed_at: datetime | None
    seller_confirmed_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    updated_at: datetime
