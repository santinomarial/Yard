# Moderation and marketplace safety

Yard treats user-generated listings, images, profiles, and messages as safety-sensitive content.

## Publication

Listings begin as drafts. A submission requires at least one approved image and no pending image. The server transitions through `PENDING_MODERATION`, runs configurable prohibited-term checks, records the moderation result, and transitions to `ACTIVE` or `REJECTED`. Active text/category/photo fields are locked so a seller cannot edit around moderation; only price, free status, condition, and coarse pickup zone are safe edits.

Image uploads are signed, size-limited, content-type allowlisted, and checked against magic bytes before moderation. Development uses a deterministic provider. Production uses Rekognition and fails safely when the required provider cannot complete.

## Reports and administration

Authenticated members can report listings, users, and messages using defined reason codes plus optional detail. Duplicate open reports are idempotent. The admin console lists the queue, moderation context, health counts, and audit history. Admin actions can dismiss, remove a listing, warn, or suspend as applicable; the reporting moderator cannot resolve their own report, and every resolution writes an `AdminAction` record.

Removal atomically cancels active reservations and pickups, removes waitlist offers, transitions the listing, and records the event. Suspended users fail authentication on subsequent requests.

## Blocking

Blocks are directional records but interaction denial is symmetric. The server enforces the relationship for new and existing messages, new conversations, individual reservations, waitlist joins/claims/promotions, and bundle reservations. A blocked waitlist member is skipped atomically. Public anonymous browse remains visible by design; authenticated discovery exclusion is documented as remaining work.

Policies are maintained in [prohibited items](prohibited-items.md), [community guidelines](community-guidelines.md), and [terms](terms-of-service.md). Support is surfaced in-app and in App Store metadata.
