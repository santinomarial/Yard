# Yard for iOS

The native Yard client uses Swift 6, SwiftUI, Observation, and structured concurrency. The checked-in Xcode project is generated deterministically from `project.yml`.

## Open and run

1. Start the local backend from the repository root with `make dev`.
2. Open `Yard.xcodeproj` in Xcode 26 or later.
3. Select an iPhone simulator and run the `Yard` scheme.

The Debug configuration connects to `http://127.0.0.1:8000`, which avoids simulator runtimes that resolve `localhost` over an unreachable IPv6 path. A physical device needs a LAN-reachable development URL configured through the `YARD_API_BASE_URL` Info property.

## Regenerate the project

Install XcodeGen 2.46 or later, then run:

```bash
xcodegen generate --spec ios/Yard/project.yml
```

Project-file changes should be generated rather than edited manually.
