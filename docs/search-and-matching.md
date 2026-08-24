# Search and matching

Yard's initial retrieval path is deliberately useful without an external AI service. PostgreSQL applies listing-state and structured filters; title and description provide lexical candidates. `EmbeddingProvider` is the boundary for a future local or hosted semantic model, and lexical retrieval remains the required fallback.

## Buying-intent score

Matches store both a score from 0 to 1 and its component values. The score is not a probability. It is a weighted compatibility measure:

| Feature | Weight | Meaning |
| --- | ---: | --- |
| Query coverage | 0.40 | Fraction of normalized query tokens present in title/description |
| Category | 0.20 | Exact category match when requested |
| Budget | 0.20 | Full credit within budget, declining above it |
| Condition | 0.10 | Listing meets the requested minimum |
| Pickup | 0.10 | Exact coarse pickup-zone match when requested |

Only supplied constraints participate in normalization, so an omitted preference cannot inflate a match. Scores at or above `0.55` are persisted. The threshold and weights are named configuration in the matching module and must be evaluated against labeled fixtures before changes.

Run the inspectable fixture evaluation with:

```bash
docker run --rm \
  -v "$PWD/scripts:/workspace:ro" \
  -v "$PWD/backend:/backend:ro" \
  -w /workspace yard-backend python evaluate_matching.py
```

Production click, save, and reservation outcomes do not exist yet and are not claimed.
