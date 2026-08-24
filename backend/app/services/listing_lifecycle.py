import uuid
from datetime import UTC, datetime

from app.models.listing import Listing, ListingStatus
from app.models.marketplace_event import ListingEvent


class InvalidListingTransition(ValueError):
    pass


LEGAL_TRANSITIONS: dict[ListingStatus, frozenset[ListingStatus]] = {
    ListingStatus.DRAFT: frozenset({ListingStatus.PENDING_MODERATION, ListingStatus.ARCHIVED}),
    ListingStatus.PENDING_MODERATION: frozenset(
        {ListingStatus.ACTIVE, ListingStatus.REJECTED, ListingStatus.ARCHIVED}
    ),
    ListingStatus.ACTIVE: frozenset(
        {ListingStatus.RESERVED, ListingStatus.SOLD, ListingStatus.ARCHIVED, ListingStatus.REMOVED}
    ),
    ListingStatus.RESERVED: frozenset(
        {ListingStatus.ACTIVE, ListingStatus.SOLD, ListingStatus.REMOVED}
    ),
    ListingStatus.SOLD: frozenset({ListingStatus.ARCHIVED}),
    ListingStatus.REJECTED: frozenset({ListingStatus.DRAFT, ListingStatus.ARCHIVED}),
    ListingStatus.ARCHIVED: frozenset({ListingStatus.ACTIVE}),
    ListingStatus.REMOVED: frozenset(),
}


def transition_listing(
    listing: Listing,
    target: ListingStatus,
    actor_id: uuid.UUID,
    event_type: str,
    event_data: dict[str, object] | None = None,
) -> ListingEvent:
    source = listing.status
    if target not in LEGAL_TRANSITIONS[source]:
        raise InvalidListingTransition(f"Cannot transition listing from {source} to {target}")
    now = datetime.now(UTC)
    listing.status = target
    listing.version = (listing.version or 1) + 1
    if target == ListingStatus.ACTIVE and listing.published_at is None:
        listing.published_at = now
    if target == ListingStatus.RESERVED:
        listing.reserved_at = now
    if target == ListingStatus.SOLD:
        listing.sold_at = now
    if target == ListingStatus.ACTIVE and source == ListingStatus.RESERVED:
        listing.reserved_at = None
    return ListingEvent(
        listing_id=listing.id,
        actor_id=actor_id,
        event_type=event_type,
        from_status=source.value,
        to_status=target.value,
        event_data=event_data or {},
    )
