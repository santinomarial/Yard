from dataclasses import dataclass
from typing import Protocol

from app.models.listing import Listing


@dataclass(frozen=True)
class ModerationDecision:
    approved: bool
    provider: str
    reasons: list[str]


class ListingModerationProvider(Protocol):
    async def moderate(self, listing: Listing) -> ModerationDecision: ...


class DeterministicDevelopmentModeration:
    prohibited_terms = frozenset(
        {
            "ammunition",
            "counterfeit",
            "explosive",
            "firearm",
            "nicotine",
            "prescription drug",
            "stolen",
            "weapon",
        }
    )

    async def moderate(self, listing: Listing) -> ModerationDecision:
        text = f"{listing.title} {listing.description}".lower()
        matches = sorted(term for term in self.prohibited_terms if term in text)
        return ModerationDecision(
            approved=not matches,
            provider="deterministic-development",
            reasons=[f"prohibited_term:{term}" for term in matches],
        )
