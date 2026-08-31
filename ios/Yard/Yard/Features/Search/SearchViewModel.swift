import Foundation
import Observation

@MainActor
@Observable
final class SearchViewModel {
    enum State: Equatable {
        case idle
        case loading
        case results
        case empty
        case failed(message: String)
    }

    var filters = ListingFilters()
    private(set) var results: [Listing] = []
    private(set) var total = 0
    private(set) var state = State.idle
    private(set) var categories: [YardCategory] = []

    init(category: String? = nil) {
        filters.category = category
    }

    var activeFilterCount: Int {
        var count = 0
        if filters.category != nil { count += 1 }
        if filters.subcategory != nil { count += 1 }
        if filters.condition != nil { count += 1 }
        if filters.minimumPriceCents != nil || filters.maximumPriceCents != nil { count += 1 }
        if filters.freeOnly { count += 1 }
        if filters.pickupZone != nil { count += 1 }
        if filters.maximumAgeDays != nil { count += 1 }
        if filters.sort != .recommended { count += 1 }
        return count
    }

    func loadCategories(using repository: any MarketplaceRepository) async {
        guard categories.isEmpty else { return }
        categories = (try? await repository.categories()) ?? []
    }

    func search(using repository: any MarketplaceRepository) async {
        state = .loading
        do {
            let page = try await repository.listings(filters: filters)
            try Task.checkCancellation()
            results = page.items
            total = page.total
            state = results.isEmpty ? .empty : .results
        } catch is CancellationError {
            return
        } catch {
            state = .failed(message: "Search is unavailable right now. Please try again.")
        }
    }

    func resetFilters() {
        let query = filters.query
        filters = ListingFilters(query: query)
    }
}
