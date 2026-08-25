import SwiftData
import SwiftUI

struct HomeView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.modelContext) private var modelContext
    @State private var model = HomeViewModel()

    private let columns = [
        GridItem(.flexible(), spacing: YardTheme.Spacing.medium),
        GridItem(.flexible(), spacing: YardTheme.Spacing.medium),
    ]

    var body: some View {
        Group {
            switch model.state {
            case .idle where model.listings.isEmpty,
                 .loading where model.listings.isEmpty:
                ProgressView("Loading nearby items…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case let .failed(message) where model.listings.isEmpty:
                ContentUnavailableView {
                    Label("Marketplace unavailable", systemImage: "wifi.exclamationmark")
                } description: {
                    Text(message)
                } actions: {
                    Button("Try again") {
                        Task { await model.reload(using: environment.marketplace) }
                    }
                    .buttonStyle(.borderedProminent)
                }
            default:
                marketplace
            }
        }
        .background(YardTheme.Colors.background)
        .navigationTitle("Yard")
        .navigationBarTitleDisplayMode(.large)
        .navigationDestination(for: Listing.self) { ListingDetailView(listing: $0) }
        .task {
            let cached = MarketplaceLocalStore.cachedMarketplace(context: modelContext)
            model.restoreCached(listings: cached.listings, categories: cached.categories)
            await model.load(using: environment.marketplace)
            if case .loaded = model.state {
                MarketplaceLocalStore.replaceMarketplace(
                    listings: model.listings,
                    categories: model.categories,
                    context: modelContext
                )
            }
            if let token = environment.session.accessToken {
                await model.loadRecommendations(using: environment.buyer, accessToken: token)
            }
        }
    }

    private var marketplace: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: YardTheme.Spacing.large) {
                Button {
                    NotificationCenter.default.post(name: .yardSelectSearch, object: nil)
                } label: {
                    Label("What are you looking for?", systemImage: "magnifyingglass")
                        .font(.body)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(YardTheme.Spacing.medium)
                        .background(.regularMaterial)
                        .clipShape(
                            RoundedRectangle(cornerRadius: YardTheme.Radius.button, style: .continuous)
                        )
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("homeSearchPrompt")

                categorySection

                if !model.recommendations.isEmpty {
                    recommendationSection
                }

                if !model.listings.isEmpty {
                    listingSection(title: "Recently Listed", listings: model.listings)
                }

                if !model.freeListings.isEmpty {
                    freeSection
                }
            }
            .padding(.horizontal, YardTheme.Spacing.medium)
            .padding(.bottom, YardTheme.Spacing.xLarge)
        }
        .refreshable { await model.reload(using: environment.marketplace) }
    }

    private var categorySection: some View {
        VStack(alignment: .leading, spacing: YardTheme.Spacing.medium) {
            Text("Browse")
                .font(.title2.bold())

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: YardTheme.Spacing.small) {
                    ForEach(model.categories) { category in
                        Button {
                            NotificationCenter.default.post(
                                name: .yardSelectSearch,
                                object: category.slug
                            )
                        } label: {
                            Label(category.name, systemImage: category.symbol)
                                .font(.subheadline.weight(.semibold))
                                .padding(.horizontal, 14)
                                .padding(.vertical, 10)
                                .background(YardTheme.Colors.surface)
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("category_\(category.slug)")
                    }
                }
            }
        }
    }

    private var recommendationSection: some View {
        VStack(alignment: .leading, spacing: YardTheme.Spacing.medium) {
            Text("For You").font(.title2.bold())
            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(spacing: YardTheme.Spacing.medium) {
                    ForEach(model.recommendations) { recommendation in
                        NavigationLink(value: recommendation.listing) {
                            VStack(alignment: .leading, spacing: 5) {
                                ListingCard(listing: recommendation.listing)
                                Text(recommendation.reasons.first ?? "Recommended")
                                    .font(.caption)
                                    .foregroundStyle(YardTheme.Colors.crimson)
                                    .lineLimit(1)
                            }
                            .frame(width: 180)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private func listingSection(title: String, listings: [Listing]) -> some View {
        VStack(alignment: .leading, spacing: YardTheme.Spacing.medium) {
            Text(title)
                .font(.title2.bold())

            LazyVGrid(columns: columns, spacing: YardTheme.Spacing.large) {
                ForEach(listings) { listing in
                    NavigationLink(value: listing) {
                        ListingCard(listing: listing)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var freeSection: some View {
        VStack(alignment: .leading, spacing: YardTheme.Spacing.medium) {
            Text("Free Near You")
                .font(.title2.bold())

            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(spacing: YardTheme.Spacing.medium) {
                    ForEach(model.freeListings) { listing in
                        NavigationLink(value: listing) {
                            ListingCard(listing: listing)
                                .frame(width: 180)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }
}

#Preview {
    NavigationStack { HomeView() }
        .environment(AppEnvironment(marketplace: PreviewMarketplaceRepository()))
}
