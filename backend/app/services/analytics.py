import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.analytics import AnalyticsEvent

ALLOWED_EVENTS = {
    "app_opened",
    "listing_viewed",
    "search_performed",
    "listing_saved",
    "listing_created",
    "buying_intent_created",
    "reservation_requested",
    "reservation_succeeded",
    "pickup_scheduled",
    "exchange_completed",
}


def record_event(
    session: AsyncSession,
    name: str,
    *,
    user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    properties: dict[str, str | int | float | bool | None] | None = None,
) -> None:
    if not get_settings().analytics_enabled or name not in ALLOWED_EVENTS:
        return
    session.add(
        AnalyticsEvent(
            user_id=user_id,
            name=name,
            entity_type=entity_type,
            entity_id=entity_id,
            properties=properties or {},
        )
    )
