import Foundation

protocol MarketplaceRepository: Sendable {
    func categories() async throws -> [YardCategory]
    func listings(filters: ListingFilters) async throws -> ListingPage
    func listing(id: UUID) async throws -> Listing
}

actor LiveMarketplaceRepository: MarketplaceRepository {
    private let client: APIClient
    private let tokenStore: any TokenStore

    init(client: APIClient, tokenStore: any TokenStore = KeychainTokenStore()) {
        self.client = client
        self.tokenStore = tokenStore
    }

    func categories() async throws -> [YardCategory] {
        try await client.get("api/v1/categories")
    }

    func listings(filters: ListingFilters) async throws -> ListingPage {
        var items: [URLQueryItem] = []
        if !filters.query.isEmpty {
            items.append(URLQueryItem(name: "query", value: filters.query))
        }
        if let category = filters.category {
            items.append(URLQueryItem(name: "category", value: category))
        }
        if let subcategory = filters.subcategory {
            items.append(URLQueryItem(name: "subcategory", value: subcategory))
        }
        if let condition = filters.condition {
            items.append(URLQueryItem(name: "condition", value: condition.rawValue))
        }
        if let minimum = filters.minimumPriceCents {
            items.append(URLQueryItem(name: "min_price_cents", value: String(minimum)))
        }
        if let maximum = filters.maximumPriceCents {
            items.append(URLQueryItem(name: "max_price_cents", value: String(maximum)))
        }
        if filters.freeOnly {
            items.append(URLQueryItem(name: "free_only", value: "true"))
        }
        if let pickupZone = filters.pickupZone {
            items.append(URLQueryItem(name: "pickup_zone", value: pickupZone))
        }
        if let maximumAgeDays = filters.maximumAgeDays {
            items.append(URLQueryItem(name: "max_age_days", value: String(maximumAgeDays)))
        }
        items.append(URLQueryItem(name: "sort", value: filters.sort.rawValue))
        return try await client.get(
            "api/v1/listings",
            queryItems: items,
            accessToken: tokenStore.load()
        )
    }

    func listing(id: UUID) async throws -> Listing {
        try await client.get(
            "api/v1/listings/\(id.uuidString)",
            accessToken: tokenStore.load()
        )
    }
}
