import SwiftUI

@main
struct YardApp: App {
    @State private var environment = AppEnvironment.live()

    var body: some Scene {
        WindowGroup {
            AuthenticationGate()
                .environment(environment)
                .tint(YardTheme.Colors.crimson)
        }
    }
}
