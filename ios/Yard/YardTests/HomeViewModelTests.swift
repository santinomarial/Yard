import Testing
@testable import Yard

@MainActor
struct HomeViewModelTests {
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

