import uuid
from dataclasses import dataclass
from typing import Protocol

from app.models.listing import Listing, ListingCondition


@dataclass(frozen=True)
class IntentFeatures:
    query: str
    category_id: uuid.UUID | None
    maximum_price_cents: int | None
    minimum_condition: ListingCondition | None
    pickup_zone: str | None


@dataclass(frozen=True)
class MatchScore:
    total: float
    components: dict[str, float]


WEIGHTS = {"text": 0.4, "category": 0.2, "price": 0.2, "condition": 0.1, "pickup": 0.1}
CONDITION_RANK = {
    ListingCondition.FAIR: 0,
    ListingCondition.GOOD: 1,
    ListingCondition.LIKE_NEW: 2,
    ListingCondition.NEW: 3,
}


def token_similarity(left: str, right: str) -> float:
    left_tokens = {token.strip(".,!?'\"") for token in left.lower().split() if token}
    right_tokens = {token.strip(".,!?'\"") for token in right.lower().split() if token}
    return len(left_tokens & right_tokens) / len(left_tokens) if left_tokens else 0


class EmbeddingProvider(Protocol):
    """Optional semantic provider; lexical scoring remains available without one."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


def score_match(intent: IntentFeatures, listing: Listing) -> MatchScore:
    text = token_similarity(intent.query, f"{listing.title} {listing.description}")
    category = 1.0 if intent.category_id == listing.category_id else 0.0
    if intent.maximum_price_cents is None:
        price = 0.0
    elif listing.price_cents <= intent.maximum_price_cents:
        price = 1.0
    else:
        price = max(
            0.0,
            1 - (listing.price_cents - intent.maximum_price_cents) / max(listing.price_cents, 1),
        )
    condition = (
        1.0
        if intent.minimum_condition is not None
        and CONDITION_RANK[listing.condition] >= CONDITION_RANK[intent.minimum_condition]
        else 0.0
    )
    pickup = 1.0 if intent.pickup_zone == listing.pickup_zone else 0.0
    components = {
        "text": text,
        "category": category,
        "price": price,
        "condition": condition,
        "pickup": pickup,
    }
    active = {"text"}
    if intent.category_id is not None:
        active.add("category")
    if intent.maximum_price_cents is not None:
        active.add("price")
    if intent.minimum_condition is not None:
        active.add("condition")
    if intent.pickup_zone is not None:
        active.add("pickup")
    active_weight = sum(WEIGHTS[name] for name in active)
    total = sum(components[name] * WEIGHTS[name] for name in active) / active_weight
    return MatchScore(round(total, 4), {key: round(value, 4) for key, value in components.items()})
