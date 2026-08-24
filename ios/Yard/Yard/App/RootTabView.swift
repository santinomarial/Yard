import SwiftUI
import SwiftData

struct RootTabView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.modelContext) private var modelContext
    @State private var selectedTab = YardTab.home
    @State private var selectedSearchCategory: String?
    @State private var homePath: [DeepLinkRoute] = []
    @State private var profilePath: [DeepLinkRoute] = []

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack(path: $homePath) {
                HomeView()
                    .navigationDestination(for: DeepLinkRoute.self) { route in
                        DeepLinkedDestinationView(route: route)
                    }
            }
            .tabItem { Label("Home", systemImage: "house") }
            .tag(YardTab.home)

            NavigationStack {
                SearchView(category: selectedSearchCategory)
                    .id(selectedSearchCategory)
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

            NavigationStack(path: $profilePath) {
                ProfileView()
                    .navigationDestination(for: DeepLinkRoute.self) { route in
                        DeepLinkedDestinationView(route: route)
                    }
            }
            .tabItem { Label("Profile", systemImage: "person.crop.circle") }
            .tag(YardTab.profile)
        }
        .accessibilityIdentifier("rootTabView")
        .safeAreaInset(edge: .top, spacing: 0) {
            if !environment.connectivity.isConnected {
                Label("Offline · showing saved data", systemImage: "wifi.slash")
                    .font(.caption.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 6)
                    .background(.orange)
                    .foregroundStyle(.black)
                    .accessibilityIdentifier("offlineBanner")
            }
        }
        .task {
            guard !ProcessInfo.processInfo.arguments.contains("-ui-testing") else { return }
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
        .onReceive(NotificationCenter.default.publisher(for: .yardSelectSearch)) { note in
            selectedSearchCategory = note.object as? String
            selectedTab = .search
        }
        .onOpenURL(perform: route)
        .onContinueUserActivity(NSUserActivityTypeBrowsingWeb) { activity in
            guard let url = activity.webpageURL else { return }
            route(url)
        }
        .task(id: environment.connectivity.isConnected) {
            guard environment.connectivity.isConnected,
                  let token = environment.session.accessToken
            else { return }
            await MarketplaceLocalStore.syncPendingFavorites(
                context: modelContext,
                repository: environment.buyer,
                accessToken: token
            )
        }
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
        guard let destination = DeepLinkRoute(url: url) else { return }
        switch destination {
        case .listing:
            selectedTab = .home
            homePath = [destination]
        case .conversation, .reservation:
            selectedTab = .profile
            profilePath = [destination]
        case .waitlist:
            selectedTab = .saved
        }
    }
}

enum DeepLinkRoute: Hashable {
    case listing(UUID)
    case conversation(UUID)
    case reservation(UUID)
    case waitlist

    init?(url: URL) {
        let components = url.pathComponents.filter { $0 != "/" }
        let kind: String?
        let identifier: String?
        if url.scheme?.lowercased() == "yard" {
            kind = url.host?.lowercased()
            identifier = components.first
        } else if url.scheme?.lowercased() == "https" {
            kind = components.first?.lowercased()
            identifier = components.dropFirst().first
        } else {
            return nil
        }
        switch kind {
        case "listing", "listings":
            guard let identifier, let id = UUID(uuidString: identifier) else { return nil }
            self = .listing(id)
        case "conversation", "conversations":
            guard let identifier, let id = UUID(uuidString: identifier) else { return nil }
            self = .conversation(id)
        case "reservation", "reservations":
            guard let identifier, let id = UUID(uuidString: identifier) else { return nil }
            self = .reservation(id)
        case "waitlist": self = .waitlist
        default: return nil
        }
    }
}

private struct DeepLinkedDestinationView: View {
    let route: DeepLinkRoute
    @Environment(AppEnvironment.self) private var environment
    @State private var state = LoadState.loading

    var body: some View {
        Group {
            switch state {
            case .loading:
                ProgressView("Opening Yard…")
            case let .listing(listing):
                ListingDetailView(listing: listing)
            case let .conversation(conversation):
                ChatView(conversation: conversation, listingTitle: "Yard conversation")
            case let .reservation(reservation):
                PickupCoordinatorView(reservation: reservation)
            case .unavailable:
                ContentUnavailableView(
                    "No longer available",
                    systemImage: "shippingbox",
                    description: Text("This Yard link has expired or you no longer have access.")
                )
            }
        }
        .task(id: route) { await load() }
    }

    private func load() async {
        do {
            switch route {
            case let .listing(id):
                state = .listing(try await environment.marketplace.listing(id: id))
            case let .conversation(id):
                guard let token = environment.session.accessToken,
                      let conversation = try await environment.transactions
                        .conversations(accessToken: token).first(where: { $0.id == id })
                else { state = .unavailable; return }
                state = .conversation(conversation)
            case let .reservation(id):
                guard let token = environment.session.accessToken,
                      let reservation = try await environment.transactions
                        .reservations(accessToken: token).first(where: { $0.id == id })
                else { state = .unavailable; return }
                state = .reservation(reservation)
            case .waitlist:
                state = .unavailable
            }
        } catch {
            state = .unavailable
        }
    }

    private enum LoadState {
        case loading
        case listing(Listing)
        case conversation(Conversation)
        case reservation(Reservation)
        case unavailable
    }
}

private enum YardTab: Hashable {
    case home
    case search
    case sell
    case saved
    case profile
}

#Preview {
    RootTabView()
        .environment(AppEnvironment.live())
}
