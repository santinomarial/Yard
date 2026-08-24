# App Review demo access

App Review personnel may not have a Harvard-managed email. Yard uses time-limited, single-use review invitations instead of a universal production bypass.

## Release workflow

1. An authorized operator generates one cryptographically random review code for the submitted version. Only its keyed hash is stored, with a purpose, creation audit, expiration no more than 72 hours away, and unused status.
2. Put the plain code only in the private App Review notes in App Store Connect. Never commit it, email it broadly, or reuse it for TestFlight groups.
3. The reviewer installs the submitted build and completes Sign in with Apple, then chooses **App Review access** on the eligibility screen and redeems the code.
4. Redemption atomically binds that invitation to the signed-in Apple-backed Yard account, marks only that account eligible, and consumes the code. Concurrent or repeated redemption fails.
5. The operator revokes or expires the review grant after the review window and creates a different invitation for a later submission.

The normal Harvard email path remains unchanged. The review endpoint must rate-limit attempts, store only keyed code hashes, reject expired/used/revoked invitations, emit an audit event, and never accept a static environment-variable master code. Development auth remains unavailable in production.

## Suggested review note

“Yard normally verifies eligibility with a Harvard-managed email. For App Review, sign in with Apple, choose App Review access, and enter the single-use code below. The code expires at `[UTC timestamp]` and can activate only the Apple-backed account that redeems it. Yard does not process payments. All seeded people and listings are fictional. Account deletion is in Profile → Delete account. Report and block controls are available from listings and conversations.”

Do not submit until the invitation migration, operator generation command, authenticated redemption endpoint, iOS redemption surface, and expiry/revocation procedure have passed their tests for the release candidate.
