# Delivery plan

Yard is built as independently verifiable vertical slices. The repository should remain runnable at every checkpoint.

1. Repository and core marketplace
2. Authentication and Harvard email verification
3. Selling and listing moderation
4. Buying intents, matching, and recommendations
5. Transactional reservations, waitlists, and bundles
6. Messaging and pickup coordination
7. Moderation and administration
8. Offline resilience and synchronization
9. Production hardening and App Store preparation

Each phase is committed and pushed only after the checks appropriate to that phase pass. External services are represented by production-ready boundaries and honest local implementations until credentials are configured.

