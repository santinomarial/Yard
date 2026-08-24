# Backend architecture

FastAPI exposes `/api/v1` resources over a SQLAlchemy 2 async persistence layer. Route modules translate HTTP contracts; service modules own state transitions and transactional behavior; Pydantic schemas own public payloads.

## Domains

- Authentication validates Apple JWTs and manages hashed Harvard-email and App Review grants.
- Listings own draft/publish/archive/relist transitions, signed uploads, image state, text policy checks, embeddings, and seller-safe edits.
- Buyer services own saves, intents, explainable matches, and lightweight recommendations.
- Reservations own leases, idempotency, waitlists, bundle allocation, cancellation, expiration, and completion handoff.
- Messaging owns conversation membership, persisted history, read state, WebSocket delivery, block enforcement, and notification enqueueing.
- Pickup owns public zones, proposals, acceptance, coarse ETA/status, cancellation, and dual-party completion.
- Safety owns reports, moderation actions, takedown/suspension, and immutable admin action logs.

## Data and transactions

Alembic migrations are the schema history. PostgreSQL is configured with pgvector and full-text indexes. Row-level locks protect contested listing/reservation state; partial unique constraints add database-level invariants. SQLite is used only for fast isolated API/unit tests, while concurrency and vector behavior run against PostgreSQL.

## Jobs and reliability

The worker repeatedly expires durable reservation leases, schedules due notifications, and delivers queued notifications idempotently. It reports structured counts and job failures. Publication currently performs deterministic text review, image provider completion, embedding write, and intent matching in the request path; this keeps local behavior simple but should move to durable job records before significant traffic. Provider interfaces already separate APNs, SES, embeddings, image moderation, and object storage.

## Security and observability

Middleware applies request IDs, safe error envelopes, body-size limits, security headers, structured latency logs, and rate limits. Authorization checks live beside protected resource loading. Metrics cover HTTP latency, search, reservation conflicts/expirations, notifications, moderation, and worker failures. Analytics are first-party, allowlisted, configurable, and do not claim outcomes that have not occurred.
