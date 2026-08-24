import math

from app.services.embeddings import EMBEDDING_DIMENSIONS, local_embedding


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def test_local_embedding_is_deterministic_and_normalized() -> None:
    first = local_embedding("Dell monitor for coding")
    second = local_embedding("Dell monitor for coding")

    assert first == second
    assert len(first) == EMBEDDING_DIMENSIONS
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)


def test_aliases_improve_semantic_retrieval_without_external_service() -> None:
    query = local_embedding("cheap second screen")
    monitor = local_embedding("Dell computer monitor")
    unrelated = local_embedding("calculus textbook")

    assert cosine(query, monitor) > cosine(query, unrelated)
