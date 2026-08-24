import uuid

from app.models import Listing, ListingCondition, ListingStatus
from app.services.matching import IntentFeatures, score_match


def test_matching_score_is_explainable_and_rewards_compatibility() -> None:
    category = uuid.uuid4()
    listing = Listing(
        seller_id=uuid.uuid4(),
        title="Dell coding monitor",
        description="27 inch display",
        category_id=category,
        price_cents=8500,
        is_free=False,
        condition=ListingCondition.GOOD,
        status=ListingStatus.ACTIVE,
        pickup_zone="Kirkland House area",
    )
    compatible = score_match(
        IntentFeatures(
            "coding monitor", category, 12000, ListingCondition.GOOD, "Kirkland House area"
        ),
        listing,
    )
    incompatible = score_match(
        IntentFeatures("road bike", uuid.uuid4(), 2000, ListingCondition.NEW, "SEC"), listing
    )
    assert compatible.total > incompatible.total
    assert compatible.components == {
        "text": 1.0,
        "category": 1.0,
        "price": 1.0,
        "condition": 1.0,
        "pickup": 1.0,
    }
    assert compatible.total == 1.0
