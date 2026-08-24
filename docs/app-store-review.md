# App Review demo access

App Review personnel may not have a Harvard-managed email. Yard uses time-limited, single-use review invitations instead of a universal production bypass.

## Release workflow

1. After deploying migration `20260824_0016`, an authorized operator generates one cryptographically random review code for the submitted version. Only its keyed hash is stored, with a purpose, creation audit, expiration no more than 72 hours away, and unused status:

   ```bash
   docker compose exec backend python -m scripts.create_review_invite \
     --purpose "App Store 1.0 build 1" --created-by "release-operator" --hours 48
   ```
2. Put the plain code only in the private App Review notes in App Store Connect. Never commit it, email it broadly, or reuse it for TestFlight groups.
3. The reviewer installs the submitted build and completes Sign in with Apple, then chooses **App Review access** on the eligibility screen and redeems the code.
4. Redemption atomically binds that invitation to the signed-in Apple-backed Yard account, marks only that account eligible, and consumes the code. Concurrent or repeated redemption fails.
5. The operator revokes the invitation/grant after the review window (or lets it expire) and creates a different invitation for a later submission:

   ```bash
   docker compose exec backend python -m scripts.revoke_review_invite INVITE_UUID
   ```

The normal Harvard email path remains unchanged. The review endpoint must rate-limit attempts, store only keyed code hashes, reject expired/used/revoked invitations, emit an audit event, and never accept a static environment-variable master code. Development auth remains unavailable in production.

## Suggested review note

“Yard normally verifies eligibility with a Harvard-managed email. For App Review, sign in with Apple, choose App Review access, and enter the single-use code below. The code expires at `[UTC timestamp]` and can activate only the Apple-backed account that redeems it. Yard does not process payments. All seeded people and listings are fictional. Account deletion is in Profile → Delete account. Report and block controls are available from listings and conversations.”

The implementation includes the invitation migration, operator generation/revocation commands, authenticated and rate-limited redemption endpoint, iOS redemption surface, expiry enforcement, single-use row lock, and automated tests. Exercise the complete flow again against the release deployment before placing a fresh code in App Store Connect.
