import hashlib
import math
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing

EMBEDDING_DIMENSIONS = 96
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
ALIASES = {
    "screen": "monitor",
    "display": "monitor",
    "coding": "computer",
    "programming": "computer",
    "notebook": "laptop",
    "refrigerator": "fridge",
    "couch": "sofa",
    "cycle": "bike",
    "bicycle": "bike",
    "earphones": "headphones",
}


def local_embedding(value: str) -> list[float]:
    """Create a deterministic, dependency-free semantic hashing embedding."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = [ALIASES.get(token, token) for token in TOKEN_PATTERN.findall(value.lower())]
    for token in tokens:
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        index = int.from_bytes(digest[:4]) % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(component * component for component in vector))
    if norm:
        return [component / norm for component in vector]
    return vector


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


async def write_listing_embedding(session: AsyncSession, listing: Listing) -> None:
    if session.bind is None or session.bind.dialect.name != "postgresql":
        return
    embedding = local_embedding(f"{listing.title} {listing.description}")
    await session.execute(
        text("UPDATE listings SET embedding = CAST(:embedding AS vector) WHERE id = :listing_id"),
        {"embedding": vector_literal(embedding), "listing_id": listing.id},
    )


async def refresh_listing_embeddings(session: AsyncSession) -> int:
    if session.bind is None or session.bind.dialect.name != "postgresql":
        return 0
    rows = await session.execute(
        text("SELECT id, title, description FROM listings WHERE embedding IS NULL")
    )
    updated = 0
    for listing_id, title, description in rows:
        await session.execute(
            text(
                "UPDATE listings SET embedding = CAST(:embedding AS vector) WHERE id = :listing_id"
            ),
            {
                "embedding": vector_literal(local_embedding(f"{title} {description}")),
                "listing_id": listing_id,
            },
        )
        updated += 1
    return updated
