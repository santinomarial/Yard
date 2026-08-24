# App Store readiness

The native target uses project-controlled marketing/build versions, distinct debug/production APNs entitlements, a production API URL build setting, Universal Links entitlement architecture, purpose strings, a privacy manifest, an opaque 1024px icon, account deletion, and in-app policy/support surfaces.

Before release, the operator must replace the `yard.market` domains and email placeholders, host the Apple App Site Association file, configure the Apple team/bundle/App ID and Sign in with Apple capability, provision APNs keys, publish policies over HTTPS, and complete the App Store checklist. Xcode and Apple credentials are intentionally not embedded in the repository.

Release builds fail fast when their API URL is missing; they do not silently fall back to localhost. Debug builds retain localhost for simulator development. The app supports iOS 18+ and the project is generated for Xcode 26 compatibility.
