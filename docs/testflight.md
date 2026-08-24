# TestFlight release procedure

1. Replace placeholder domains and support contact details; verify HTTPS, Universal Links, SES, APNs, S3 delivery, and the published privacy/terms URLs.
2. Set the marketing version and monotonically increasing build number in `ios/Yard/project.yml`, regenerate the Xcode project, and commit both files.
3. Run backend/admin checks, PostgreSQL integrations, k6 smoke, and the GitHub macOS iOS job. Resolve every warning that affects signing, privacy manifests, or required-reason APIs.
4. In Xcode 26 or later, select the Release configuration and production team, archive a generic iOS device build, validate the archive, then upload it to App Store Connect.
5. Complete export-compliance and App Privacy answers from `docs/app-store/metadata-checklist.md`; attach the review notes and a single-use review access code described in `docs/app-store-review.md`.
6. Test with an internal group first: clean install, Sign in with Apple, verification/review access, sell with camera and library, natural search, reservation race behavior, chat/push, pickup/Live Activity, report/block, and account deletion.
7. Expand to a small external beta only after crash, moderation, support, backup, and incident-response paths are owned. Do not describe local benchmark results as production behavior.
