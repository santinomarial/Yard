# iOS architecture

The iOS app is native SwiftUI with feature-scoped observable state and repository actors. Views own presentation state; repositories own remote calls; SwiftData owns safe local state.

## Application flow

`AuthenticationGate` restores the Keychain token, drives Sign in with Apple, Harvard-email verification, terms acceptance, and secure App Review redemption. `RootTabView` provides Home, Search, Sell, Saved, and Profile navigation and routes Yard custom links from notifications. Release entitlements include the associated-domain boundary; hosted HTTPS Universal Link routing remains a release task.

## Feature state and networking

Observation-based view models are `@MainActor`; network and upload work runs asynchronously through actor-backed repositories and `APIClient`. The client renders typed error envelopes and does not optimistically claim successful reservations, publication, messages, pickup completion, or account mutation.

## Local-first boundaries

SwiftData caches listing/category snapshots, favorites, draft groups/photos, and conversation summaries. Draft images are prepared locally, and favorites can queue for retry. Connectivity-required actions stay explicit. Cache records are disposable and never override the server’s listing/reservation version.

## Apple frameworks

- PhotosUI and the camera collect listing images.
- Vision performs OCR/classification suggestions behind `ItemAnalysisService`; the seller reviews every draft.
- MapKit/Core Location calculate walking ETA on-device and send only coarse ETA/status.
- AuthenticationServices supplies Apple identity credentials for server validation.
- UserNotifications registers/revokes APNs tokens and routes deep links.
- ActivityKit/WidgetKit show an expiring pickup Live Activity and Dynamic Island presentation.

## Accessibility and presentation

`YardTheme` centralizes color, spacing, surfaces, button styles, and contrast-aware semantic colors. Screens use semantic SwiftUI controls, Dynamic Type fonts, meaningful labels, and identifiers on critical actions. Final VoiceOver, largest-text, Reduce Motion, dark-mode, and high-contrast device passes remain release gates because this environment has no Xcode runtime.
