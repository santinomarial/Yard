import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BundleCreate(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    price_cents: int = Field(gt=0, le=10_000_000)
    listing_ids: list[uuid.UUID] = Field(min_length=2, max_length=20)


class BundleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    seller_id: uuid.UUID
    title: str
    price_cents: int
    is_active: bool
    listing_ids: list[uuid.UUID]


class BundleReserve(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100)


class BundleReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    bundle_id: uuid.UUID
    buyer_id: uuid.UUID
    expires_at: datetime
    created_at: datetime
