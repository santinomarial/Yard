import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import NotificationStatus


class DeviceTokenCreate(BaseModel):
    token: str = Field(min_length=32, max_length=255, pattern=r"^[A-Fa-f0-9]+$")
    environment: str = Field(default="sandbox", pattern=r"^(sandbox|production)$")


class DeviceTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    environment: str
    created_at: datetime


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    notification_type: str
    title: str
    body: str
    deep_link: str | None
    data: dict[str, str | int | float | bool | None]
    status: NotificationStatus
    sent_at: datetime | None
    created_at: datetime
