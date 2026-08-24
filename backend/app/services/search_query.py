import re
from dataclasses import dataclass

PRICE_PATTERN = re.compile(
    r"\b(?:under|below|max(?:imum)?|less\s+than)\s*\$?\s*(\d+(?:\.\d{1,2})?)\b",
    re.IGNORECASE,
)
FREE_PATTERN = re.compile(r"\bfree\b", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedSearchQuery:
    text: str | None
    maximum_price_cents: int | None
    free_only: bool


def parse_natural_search(query: str | None) -> ParsedSearchQuery:
    if not query or not query.strip():
        return ParsedSearchQuery(text=None, maximum_price_cents=None, free_only=False)

    maximum_price_cents: int | None = None
    price_match = PRICE_PATTERN.search(query)
    if price_match:
        maximum_price_cents = min(round(float(price_match.group(1)) * 100), 10_000_000)

    free_only = FREE_PATTERN.search(query) is not None
    cleaned = PRICE_PATTERN.sub(" ", query)
    cleaned = FREE_PATTERN.sub(" ", cleaned) if free_only else cleaned
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    return ParsedSearchQuery(
        text=cleaned or None,
        maximum_price_cents=maximum_price_cents,
        free_only=free_only,
    )
