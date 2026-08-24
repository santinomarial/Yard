import SwiftUI

struct SavedView: View {
    @Environment(AppEnvironment.self) private var environment
    @State private var model = SavedViewModel()
    @State private var showsIntentComposer = false

    var body: some View {
        Group {
            switch model.state {
            case .loading where model.listings.isEmpty && model.intents.isEmpty:
                ProgressView("Loading saved items…")
            case let .failed(message) where model.listings.isEmpty && model.intents.isEmpty:
                ContentUnavailableView {
                    Label("Saved items unavailable", systemImage: "wifi.exclamationmark")
                } description: { Text(message) } actions: {
                    Button("Try again") { Task { await load() } }
                }
            default:
                content
            }
        }
        .navigationTitle("Saved")
        .background(YardTheme.Colors.background)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Create wanted alert", systemImage: "bell.badge") {
                    showsIntentComposer = true
                }
                .accessibilityIdentifier("createWantedAlertButton")
            }
        }
        .sheet(isPresented: $showsIntentComposer) {
            BuyingIntentComposer { draft in
                guard let token = environment.session.accessToken else { return false }
                return await model.createIntent(draft, using: environment.buyer, accessToken: token)
            }
        }
        .navigationDestination(for: Listing.self) { ListingDetailView(listing: $0) }
        .navigationDestination(for: BuyingIntent.self) { IntentMatchesView(intent: $0) }
        .task { await load() }
        .refreshable { await load() }
        .accessibilityIdentifier("savedView")
    }

    private var content: some View {
        List {
            Section("Wanted alerts") {
                if model.intents.isEmpty {
                    Text("Create an alert and Yard will match newly listed items.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(model.intents) { intent in
                        NavigationLink(value: intent) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(intent.query).font(.headline)
                                Text(intent.summary).font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }

            Section("Saved items") {
                if model.listings.isEmpty {
                    Text("Save a listing to keep it here.").foregroundStyle(.secondary)
                } else {
                    ForEach(model.listings) { listing in
                        NavigationLink(value: listing) {
                            SavedListingRow(listing: listing)
                        }
                        .swipeActions {
                            Button("Remove", role: .destructive) {
                                guard let token = environment.session.accessToken else { return }
                                Task {
                                    await model.remove(
                                        listing, using: environment.buyer, accessToken: token
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
    }

    private func load() async {
        guard let token = environment.session.accessToken else { return }
        await model.load(using: environment.buyer, accessToken: token)
    }
}

struct SavedListingRow: View {
    let listing: Listing

    var body: some View {
        HStack(spacing: YardTheme.Spacing.medium) {
            ListingImage(listing: listing)
                .frame(width: 84, height: 84)
                .clipShape(RoundedRectangle(cornerRadius: YardTheme.Radius.small))
            VStack(alignment: .leading, spacing: 5) {
                Text(listing.title).font(.headline).lineLimit(2)
                Text(listing.formattedPrice).foregroundStyle(
                    listing.isFree ? YardTheme.Colors.crimson : .primary
                )
                Label(listing.pickupZone, systemImage: "mappin.and.ellipse")
                    .font(.caption).foregroundStyle(.secondary).lineLimit(1)
            }
        }
        .accessibilityElement(children: .combine)
    }
}

#Preview {
    NavigationStack { SavedView() }
        .environment(AppEnvironment(marketplace: PreviewMarketplaceRepository()))
}
