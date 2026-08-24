import Testing
@testable import Yard

@MainActor
struct HomeViewModelTests {
    @Test
    func cachedMarketplaceIsImmediatelyBrowsable() {
        let model = HomeViewModel()

        model.restoreCached(
            listings: Listing.previewListings,
            categories: YardCategory.previewCategories
        )

        #expect(model.listings == Listing.previewListings)
        #expect(model.state == .loaded)
    }

    @Test
    func loadsCategoriesAndListingsTogether() async {
        let model = HomeViewModel()
        let repository = PreviewMarketplaceRepository()

        await model.load(using: repository)

        #expect(model.state == .loaded)
        #expect(model.categories.count == 3)
        #expect(model.listings.count == 2)
        #expect(model.freeListings.map(\.title) == ["Floor Lamp"])
    }
}
