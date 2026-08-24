import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.listing import ListingCondition, ListingStatus
from app.schemas.listing_image import ListingImageRead


class ListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    title: str
    description: str
    category_id: uuid.UUID
    subcategory_id: uuid.UUID | None
    category_name: str
    subcategory_name: str | None
    price_cents: int
    is_free: bool
    condition: ListingCondition
    status: ListingStatus
    pickup_zone: str
    image_url: str | None
    images: list[ListingImageRead]
    published_at: datetime | None
    view_count: int
    save_count: int


class ListingPage(BaseModel):
    items: list[ListingRead]
    total: int
    limit: int
    offset: int


class ListingQuery(BaseModel):
    query: str | None = Field(default=None, max_length=120)
    category: str | None = None
    condition: ListingCondition | None = None
    min_price_cents: int | None = Field(default=None, ge=0)
    max_price_cents: int | None = Field(default=None, ge=0)
    free_only: bool = False
    pickup_zone: str | None = None
    sort: str = "newest"
    limit: int = Field(default=30, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ListingDraftCreate(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(min_length=3, max_length=5_000)
    category_id: uuid.UUID
    subcategory_id: uuid.UUID | None = None
    price_cents: int = Field(ge=0, le=10_000_000)
    is_free: bool = False
    condition: ListingCondition
    pickup_zone: str = Field(min_length=2, max_length=100)
