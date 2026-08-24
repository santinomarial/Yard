import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.listing import ListingCondition
from app.schemas.listing import ListingRead


class BuyingIntentCreate(BaseModel):
    query: str = Field(min_length=2, max_length=140)
    category_id: uuid.UUID | None = None
    maximum_price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    minimum_condition: ListingCondition | None = None
    pickup_zone: str | None = Field(default=None, max_length=100)


class BuyingIntentRead(BuyingIntentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    buyer_id: uuid.UUID
    is_active: bool
    created_at: datetime


class ListingMatchRead(BaseModel):
    id: uuid.UUID
    score: float
    score_components: dict[str, float]
    listing: ListingRead


class RecommendationRead(BaseModel):
    score: float
    reasons: list[str]
    listing: ListingRead
