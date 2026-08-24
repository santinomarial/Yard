import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.listing_image import ListingImageStatus


class ListingImageUploadRequest(BaseModel):
    content_type: str = Field(max_length=80)
    byte_size: int = Field(gt=0, le=10 * 1024 * 1024)
    sort_order: int = Field(default=0, ge=0, le=7)


class ListingImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_type: str
    byte_size: int
    sort_order: int
    status: ListingImageStatus
    url: str | None
    moderation_reasons: list[str]
    uploaded_at: datetime | None


class ListingImageUploadRead(BaseModel):
    image: ListingImageRead
    upload_url: str
    required_headers: dict[str, str]
    expires_in_seconds: int
