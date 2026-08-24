import Foundation
import Testing
@testable import Yard

@MainActor
struct SavedViewModelTests {
    @Test
    func cachedFavoriteCanBeRemovedOffline() {
        let model = SavedViewModel()
        model.restoreCached(Listing.previewListings)

        model.removeCached(Listing.previewListings[0])

        #expect(model.listings.count == Listing.previewListings.count - 1)
    }

    @Test
    func loadsSavedListingsAndIntentsTogether() async {
        let repository = BuyerRepositoryStub()
        let model = SavedViewModel()

        await model.load(using: repository, accessToken: "token")

        #expect(model.listings == Listing.previewListings)
        #expect(model.state == .loaded)
    }

    @Test
    func failedUnsaveRestoresOptimisticListing() async {
        let repository = BuyerRepositoryStub(failWrites: true)
        let model = SavedViewModel()
        await model.load(using: repository, accessToken: "token")

        await model.remove(Listing.previewListings[0], using: repository, accessToken: "token")

        #expect(model.listings == Listing.previewListings)
    }
}

private actor BuyerRepositoryStub: BuyerRepository {
    let failWrites: Bool

    init(failWrites: Bool = false) { self.failWrites = failWrites }

    func savedListings(accessToken: String) async throws -> [Listing] { Listing.previewListings }
    func setSaved(_ saved: Bool, listingID: UUID, accessToken: String) async throws {
        if failWrites { throw APIError.transport }
    }
    func intents(accessToken: String) async throws -> [BuyingIntent] { [] }
    func createIntent(_ draft: BuyingIntentDraft, accessToken: String) async throws -> BuyingIntent {
        throw APIError.transport
    }
    func matches(intentID: UUID, accessToken: String) async throws -> [ListingMatch] { [] }
    func recommendations(accessToken: String) async throws -> [ListingRecommendation] { [] }
}
