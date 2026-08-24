# Privacy design

Yard collects the minimum data needed to establish access, publish marketplace content, coordinate an exchange, operate notifications, and investigate safety issues.

## Data used

- Apple subject identifier and a user-chosen display name for account continuity.
- Harvard email and verification time for community access; the private email is never exposed in listing payloads.
- User-authored listings, photos, buying intents, messages, reports, and public pickup-zone choices.
- Reservation/pickup state, notification token, and first-party operational/marketplace events.
- Optional on-device location for route/ETA calculation only when the member invokes pickup navigation.

## Data deliberately not used

Yard does not process payment credentials, academic records, contact lists, advertising identifiers, popularity scores, exact public addresses, dorm room numbers, or continuous movement history. ETA sharing sends minutes/status, not raw GPS coordinates.

## Retention and deletion

In-app deletion removes sign-in identities, Harvard email, device tokens, saves, and open intents; uncompleted inventory is taken down. User-authored safety/transaction records may be pseudonymized and retained narrowly for fraud, dispute, and audit integrity. The production retention schedule and legal basis must be reviewed before launch and reflected in the hosted policy.

## Client privacy

Tokens live in the device Keychain. SwiftData stores disposable marketplace caches and local drafts. `PrivacyInfo.xcprivacy` declares no tracking and documents the required-reason UserDefaults API plus linked account/content data. Camera, photo-library, location, notifications, and Live Activity capabilities have purpose-specific usage text; location is requested only in pickup context.

The public-facing policy is [privacy policy](privacy-policy.md). This document describes engineering behavior and is not a substitute for counsel-approved launch language.
