import uuid

from pydantic import BaseModel, Field

from app.services.analytics import ALLOWED_EVENTS


class AnalyticsEventCreate(BaseModel):
    name: str = Field(max_length=80)
    entity_type: str | None = Field(default=None, max_length=40)
    entity_id: uuid.UUID | None = None
    properties: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    def validate_name(self) -> None:
        if self.name not in ALLOWED_EVENTS:
            raise ValueError("Unsupported analytics event")
