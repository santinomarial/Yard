import SwiftUI

struct RootTabView: View {
    var body: some View {
        TabView {
            NavigationStack {
                HomeView()
            }
            .tabItem { Label("Home", systemImage: "house") }

            NavigationStack {
                FeaturePlaceholder(
                    title: "Search",
                    message: "Search across active campus listings.",
                    symbol: "magnifyingglass"
                )
            }
            .tabItem { Label("Search", systemImage: "magnifyingglass") }

            NavigationStack {
                FeaturePlaceholder(
                    title: "Sell",
                    message: "Create a listing from your photos.",
                    symbol: "plus.circle"
                )
            }
            .tabItem { Label("Sell", systemImage: "plus.circle") }

            NavigationStack {
                FeaturePlaceholder(
                    title: "Saved",
                    message: "Items you save will remain easy to find.",
                    symbol: "bookmark"
                )
            }
            .tabItem { Label("Saved", systemImage: "bookmark") }

            NavigationStack {
                FeaturePlaceholder(
                    title: "Profile",
                    message: "Manage your listings, account, and privacy.",
                    symbol: "person.crop.circle"
                )
            }
            .tabItem { Label("Profile", systemImage: "person.crop.circle") }
        }
        .accessibilityIdentifier("rootTabView")
    }
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
