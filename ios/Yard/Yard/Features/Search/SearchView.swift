import SwiftUI

struct SearchView: View {
    @Environment(AppEnvironment.self) private var environment
    @State private var model = SearchViewModel()
    @State private var showsFilters = false

    private let columns = [
        GridItem(.flexible(), spacing: YardTheme.Spacing.medium),
        GridItem(.flexible(), spacing: YardTheme.Spacing.medium),
    ]

    var body: some View {
        @Bindable var model = model

        Group {
            switch model.state {
            case .idle, .loading where model.results.isEmpty:
                ProgressView("Searching Yard…")
            case .empty:
                ContentUnavailableView.search(text: model.filters.query)
            case let .failed(message) where model.results.isEmpty:
                ContentUnavailableView {
                    Label("Search unavailable", systemImage: "wifi.exclamationmark")
                } description: {
                    Text(message)
                } actions: {
                    Button("Try again") {
                        Task { await model.search(using: environment.marketplace) }
                    }
                }
            default:
                resultsGrid
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(YardTheme.Colors.background)
        .navigationTitle("Search")
        .searchable(
            text: $model.filters.query,
            placement: .navigationBarDrawer(displayMode: .always),
            prompt: "Monitor, mini fridge, desk…"
        )
        .textInputAutocapitalization(.never)
        .autocorrectionDisabled()
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showsFilters = true
                } label: {
                    Label(
                        model.activeFilterCount == 0
                            ? "Filters" : "Filters, \(model.activeFilterCount) active",
                        systemImage: model.activeFilterCount == 0
                            ? "line.3.horizontal.decrease.circle"
                            : "line.3.horizontal.decrease.circle.fill"
                    )
                }
                .accessibilityIdentifier("searchFiltersButton")
            }
        }
        .sheet(isPresented: $showsFilters) {
            SearchFilterSheet(filters: $model.filters, reset: model.resetFilters)
                .presentationDetents([.medium, .large])
        }
        .navigationDestination(for: Listing.self) { ListingDetailView(listing: $0) }
        .task(id: model.filters) {
            if !model.filters.query.isEmpty {
                try? await Task.sleep(for: .milliseconds(300))
            }
            guard !Task.isCancelled else { return }
            await model.search(using: environment.marketplace)
        }
        .accessibilityIdentifier("searchView")
    }

    private var resultsGrid: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: YardTheme.Spacing.medium) {
                Text("\(model.total) \(model.total == 1 ? "item" : "items")")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                LazyVGrid(columns: columns, spacing: YardTheme.Spacing.large) {
                    ForEach(model.results) { listing in
                        NavigationLink(value: listing) {
                            ListingCard(listing: listing)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .padding(YardTheme.Spacing.medium)
        }
        .refreshable { await model.search(using: environment.marketplace) }
    }
}

private struct SearchFilterSheet: View {
    @Binding var filters: ListingFilters
    let reset: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section("Price") {
                    Toggle("Free only", isOn: $filters.freeOnly)
                    Picker("Maximum price", selection: $filters.maximumPriceCents) {
                        Text("Any price").tag(Optional<Int>.none)
                        Text("Under $25").tag(Optional(2_500))
                        Text("Under $50").tag(Optional(5_000))
                        Text("Under $100").tag(Optional(10_000))
                        Text("Under $150").tag(Optional(15_000))
                    }
                    .disabled(filters.freeOnly)
                }

                Section("Condition") {
                    Picker("Condition", selection: $filters.condition) {
                        Text("Any condition").tag(Optional<ListingCondition>.none)
                        ForEach(ListingCondition.allCases, id: \.self) { condition in
                            Text(condition.displayName).tag(Optional(condition))
                        }
                    }
                }

                Section("Sort") {
                    Picker("Sort", selection: $filters.sort) {
                        ForEach(ListingSort.allCases, id: \.self) { sort in
                            Text(sort.displayName).tag(sort)
                        }
                    }
                    .pickerStyle(.inline)
                    .labelsHidden()
                }
            }
            .navigationTitle("Filters")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Reset", action: reset)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

#Preview {
    NavigationStack { SearchView() }
        .environment(AppEnvironment(marketplace: PreviewMarketplaceRepository()))
}

