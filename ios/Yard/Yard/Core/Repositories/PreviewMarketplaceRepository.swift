import Foundation

actor PreviewMarketplaceRepository: MarketplaceRepository {
    private let previewCategories: [YardCategory]
    private let previewListings: [Listing]

    init(
        categories: [YardCategory] = YardCategory.previewCategories,
        listings: [Listing] = Listing.previewListings
    ) {
        self.previewCategories = categories
        self.previewListings = listings
    }

    func categories() async throws -> [YardCategory] {
        previewCategories
    }

    func listings(filters: ListingFilters) async throws -> ListingPage {
        var results = previewListings
        if !filters.query.isEmpty {
            results = results.filter {
                $0.title.localizedCaseInsensitiveContains(filters.query)
                    || $0.description.localizedCaseInsensitiveContains(filters.query)
            }
        }
        if let category = filters.category {
            results = results.filter { $0.categoryName.lowercased() == category.lowercased() }
        }
        if filters.freeOnly {
            results = results.filter(\.isFree)
        }
        return ListingPage(items: results, total: results.count, limit: 30, offset: 0)
    }

    func listing(id: UUID) async throws -> Listing {
        guard let listing = previewListings.first(where: { $0.id == id }) else {
            throw APIError.rejected(
                statusCode: 404,
                code: "listing_not_found",
                message: "This listing is unavailable."
            )
        }
        return listing
    }
}

extension YardCategory {
    static let previewCategories = [
        YardCategory(
            id: UUID(uuidString: "C749AD33-4A65-582D-A294-C30305647020")!,
            name: "Electronics",
            slug: "electronics",
            symbol: "desktopcomputer",
            sortOrder: 0,
            children: []
        ),
        YardCategory(
            id: UUID(uuidString: "C86D3E65-19DC-5548-A5BA-26BB518A2113")!,
            name: "Furniture",
            slug: "furniture",
            symbol: "chair.lounge",
            sortOrder: 1,
            children: []
        ),
        YardCategory(
            id: UUID(uuidString: "81D99E83-18DF-5E20-A2BA-7259AEB824A5")!,
            name: "Free",
            slug: "free",
            symbol: "gift",
            sortOrder: 2,
            children: []
        ),
    ]
}

extension Listing {
    static let previewListings = [
        Listing(
            id: UUID(uuidString: "11408445-3907-55C2-848E-8AD314EB1C7B")!,
            sellerID: UUID(uuidString: "67F936CF-C018-5EBF-94B5-59BF099885F3")!,
            title: "Dell 27\" 4K Monitor",
            description: "A sharp second screen for coding. Includes the original stand.",
            categoryID: UUID(uuidString: "C749AD33-4A65-582D-A294-C30305647020")!,
            subcategoryID: nil,
            categoryName: "Electronics",
            subcategoryName: "Monitors",
            priceCents: 8_500,
            isFree: false,
            condition: .good,
            status: .active,
            pickupZone: "Kirkland House area",
            imageURL: nil,
            publishedAt: .now,
            viewCount: 12,
            saveCount: 4
        ),
        Listing(
            id: UUID(uuidString: "BF289E0D-2D45-5B8E-8E0D-1355C337C570")!,
            sellerID: UUID(uuidString: "E9C12C60-3EF2-5DA9-8B79-F8FCF9F41E08")!,
            title: "Floor Lamp",
            description: "Warm floor lamp in good condition.",
            categoryID: UUID(uuidString: "81D99E83-18DF-5E20-A2BA-7259AEB824A5")!,
            subcategoryID: nil,
            categoryName: "Free",
            subcategoryName: nil,
            priceCents: 0,
            isFree: true,
            condition: .good,
            status: .active,
            pickupZone: "Cabot House area",
            imageURL: nil,
            publishedAt: .now.addingTimeInterval(-3_600),
            viewCount: 21,
            saveCount: 8
        ),
    ]
}

