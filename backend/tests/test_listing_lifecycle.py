import uuid

import pytest

from app.models import Listing, ListingCondition, ListingStatus
from app.services.listing_lifecycle import InvalidListingTransition, transition_listing
from app.services.moderation import DeterministicDevelopmentModeration


def listing(status: ListingStatus = ListingStatus.DRAFT) -> Listing:
    return Listing(
        id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        title="Desk lamp",
        description="A useful reading light.",
        category_id=uuid.uuid4(),
        price_cents=1_500,
        is_free=False,
        condition=ListingCondition.GOOD,
        status=status,
        pickup_zone="Harvard Square",
    )


def test_legal_transition_updates_version_and_audit_event() -> None:
    item = listing()
    actor_id = item.seller_id
    event = transition_listing(
        item,
        ListingStatus.PENDING_MODERATION,
        actor_id,
        "ListingSubmittedForModeration",
    )
    assert item.status == ListingStatus.PENDING_MODERATION
    assert item.version == 2
    assert event.from_status == "draft"
    assert event.to_status == "pending_moderation"


def test_illegal_transition_is_rejected() -> None:
    item = listing()
    with pytest.raises(InvalidListingTransition):
        transition_listing(item, ListingStatus.SOLD, item.seller_id, "ExchangeCompleted")


async def test_development_moderation_rejects_prohibited_content() -> None:
    item = listing()
    item.description = "A counterfeit item"
    decision = await DeterministicDevelopmentModeration().moderate(item)
    assert decision.approved is False
    assert decision.reasons == ["prohibited_term:counterfeit"]
