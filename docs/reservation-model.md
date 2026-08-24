# Reservation model

PostgreSQL is authoritative for Yard inventory. The iOS client never marks an item reserved optimistically.

## Single-item invariant

`reserve_listing` starts a transaction, checks the buyer-scoped idempotency key, and locks the listing row with `SELECT … FOR UPDATE OF listings`. It succeeds only from `ACTIVE`, creates a durable lease, moves the listing to `RESERVED`, and writes an audit event in the same transaction.

A partial unique index on active reservations is a second database-level defense. Contending requests serialize on the listing row; losers receive `listing_already_reserved`. Same-key retries return the original reservation and produce no duplicate effect.

## Expiration and cancellation

Leases store `expires_at` in PostgreSQL. The expiration service locks due leases with `SKIP LOCKED`, making multiple workers safe. Cancellation and expiration either return the listing to `ACTIVE` or atomically promote the oldest waitlist entry.

## Waitlists

Waitlist identities are private. Promotion changes the oldest `WAITING` entry to `OFFERED` while the listing remains `RESERVED`, so an unrelated buyer cannot reserve between release and claim. An offer has its own durable expiration timestamp.

## Bundles

Bundle reservation loads member IDs and locks every listing in UUID order. It validates all members before creating any reservation. Individual reservations use the same row lock, so a bundle race has only two legal outcomes: all bundle members are reserved together, or the individual item wins and the bundle allocates nothing.

## Evidence

`tests/integration/test_reservation_race.py` runs against PostgreSQL and proves:

- exactly one of many concurrent buyers succeeds;
- same-key retries have one logical effect;
- waitlist promotion prevents direct-buyer interleaving;
- bundle and individual reservation cannot double-allocate inventory.

