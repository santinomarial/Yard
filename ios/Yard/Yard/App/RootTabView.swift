import SwiftUI

struct RootTabView: View {
    @Environment(AppEnvironment.self) private var environment
    @State private var selectedTab = YardTab.home

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack {
                HomeView()
            }
            .tabItem { Label("Home", systemImage: "house") }
            .tag(YardTab.home)

            NavigationStack {
                SearchView()
            }
            .tabItem { Label("Search", systemImage: "magnifyingglass") }
            .tag(YardTab.search)

            NavigationStack {
                SellView()
            }
            .tabItem { Label("Sell", systemImage: "plus.circle") }
            .tag(YardTab.sell)

            NavigationStack {
                SavedView()
            }
            .tabItem { Label("Saved", systemImage: "bookmark") }
            .tag(YardTab.saved)

            NavigationStack {
                ProfileView()
            }
            .tabItem { Label("Profile", systemImage: "person.crop.circle") }
            .tag(YardTab.profile)
        }
        .accessibilityIdentifier("rootTabView")
        .task {
            await PushRegistration.requestAuthorization()
            if let token = PushRegistration.storedToken { await registerDevice(token) }
        }
        .onReceive(NotificationCenter.default.publisher(for: .yardDeviceTokenUpdated)) { note in
            guard let token = note.object as? String else { return }
            Task { await registerDevice(token) }
        }
        .onReceive(NotificationCenter.default.publisher(for: .yardDeepLinkReceived)) { note in
            guard let url = note.object as? URL else { return }
            route(url)
        }
        .onOpenURL(perform: route)
    }

    private func registerDevice(_ token: String) async {
        guard let accessToken = environment.session.accessToken else { return }
        #if DEBUG
        let apnsEnvironment = "sandbox"
        #else
        let apnsEnvironment = "production"
        #endif
        _ = try? await environment.notifications.registerDevice(
            token: token, environment: apnsEnvironment, accessToken: accessToken
        )
    }

    private func route(_ url: URL) {
        guard url.scheme == "yard" else { return }
        switch url.host {
        case "reservations", "conversations": selectedTab = .profile
        case "listings": selectedTab = .home
        case "waitlist": selectedTab = .saved
        default: selectedTab = .home
        }
    }
}

private enum YardTab: Hashable {
    case home
    case search
    case sell
    case saved
    case profile
}

struct FeaturePlaceholder: View {
    let title: String
    let message: String
    let symbol: String

    var body: some View {
        ContentUnavailableView(title, systemImage: symbol, description: Text(message))
            .navigationTitle(title)
            .background(YardTheme.Colors.background)
    }
}

#Preview {
    RootTabView()
        .environment(AppEnvironment.live())
}
