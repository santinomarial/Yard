#!/usr/bin/env python3
"""Inspect Yard's initial matching model against labeled fixtures."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.models import Listing, ListingCondition, ListingStatus  # noqa: E402
from app.services.matching import IntentFeatures, score_match  # noqa: E402


def main() -> None:
    fixture_path = Path(__file__).with_name("fixtures") / "matching.json"
    fixture = json.loads(fixture_path.read_text())
    for intent_data in fixture["intents"]:
        intent = IntentFeatures(
            query=intent_data["query"],
            category_id=None,
            maximum_price_cents=intent_data.get("maximum_price_cents"),
            minimum_condition=None,
            pickup_zone=intent_data.get("pickup_zone"),
        )
        ranked = []
        for item in fixture["listings"]:
            listing = Listing(
                id=item["id"],
                seller_id=item["seller_id"],
                title=item["title"],
                description=item["description"],
                category_id=item["category_id"],
                price_cents=item["price_cents"],
                is_free=item["price_cents"] == 0,
                condition=ListingCondition(item["condition"]),
                status=ListingStatus.ACTIVE,
                pickup_zone=item["pickup_zone"],
            )
            score = score_match(intent, listing)
            ranked.append((score.total, listing.title, score.components))
        print(f"\nIntent: {intent.query}")
        for total, title, components in sorted(ranked, reverse=True)[:3]:
            print(f"  {total:.3f}  {title}  {components}")


if __name__ == "__main__":
    main()
