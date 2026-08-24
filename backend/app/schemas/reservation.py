import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationStatus, WaitlistStatus


class ReservationCreate(BaseModel):
    listing_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=100)


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    buyer_id: uuid.UUID
    seller_id: uuid.UUID
    status: ReservationStatus
    expires_at: datetime
    created_at: datetime


class WaitlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    buyer_id: uuid.UUID
    status: WaitlistStatus
    created_at: datetime
    offer_expires_at: datetime | None
