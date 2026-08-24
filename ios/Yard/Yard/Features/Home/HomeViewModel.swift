import Foundation
import Observation

@MainActor
@Observable
final class HomeViewModel {
    enum LoadState: Equatable {
        case idle
        case loading
        case loaded
        case failed(message: String)
    }

    private(set) var categories: [YardCategory] = []
    private(set) var listings: [Listing] = []
    private(set) var recommendations: [ListingRecommendation] = []
    private(set) var state = LoadState.idle

    var freeListings: [Listing] {
        listings.filter(\.isFree)
    }

    func restoreCached(listings: [Listing], categories: [YardCategory]) {
        guard self.listings.isEmpty else { return }
        self.listings = listings
        self.categories = categories
        if !listings.isEmpty { state = .loaded }
    }

    func load(using repository: any MarketplaceRepository) async {
        guard state != .loading else { return }
        state = .loading
        do {
            async let categoryRequest = repository.categories()
            async let listingRequest = repository.listings(filters: ListingFilters())
            let (loadedCategories, page) = try await (categoryRequest, listingRequest)
            categories = loadedCategories
            listings = page.items
            state = .loaded
        } catch {
            state = .failed(message: "Yard couldn't load nearby listings. Pull to try again.")
        }
    }

    func reload(using repository: any MarketplaceRepository) async {
        state = .idle
        await load(using: repository)
    }

    func loadRecommendations(
        using repository: any BuyerRepository,
        accessToken: String
    ) async {
        do { recommendations = try await repository.recommendations(accessToken: accessToken) }
        catch { recommendations = [] }
    }
}
