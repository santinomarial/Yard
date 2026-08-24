import Testing
@testable import Yard

@MainActor
struct SearchViewModelTests {
    @Test
    func queryReturnsOnlyMatchingListings() async {
        let model = SearchViewModel()
        model.filters.query = "monitor"

        await model.search(using: PreviewMarketplaceRepository())

        #expect(model.state == .results)
        #expect(model.results.map(\.title) == ["Dell 27\" 4K Monitor"])
    }

    @Test
    func resetPreservesTheUsersQuery() {
        let model = SearchViewModel()
        model.filters.query = "desk chair"
        model.filters.freeOnly = true
        model.filters.condition = .good

        model.resetFilters()

        #expect(model.filters.query == "desk chair")
        #expect(model.activeFilterCount == 0)
    }
}

