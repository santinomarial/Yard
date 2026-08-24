import Foundation

enum ListingCondition: String, Codable, CaseIterable, Sendable {
    case new
    case likeNew = "like_new"
    case good
    case fair

    var displayName: String {
        switch self {
        case .new: "New"
        case .likeNew: "Like new"
        case .good: "Good"
        case .fair: "Fair"
        }
    }
}

enum ListingStatus: String, Codable, Sendable {
    case draft
    case pendingModeration = "pending_moderation"
    case active
    case reserved
    case sold
    case archived
    case rejected
    case removed

    var displayName: String {
        switch self {
        case .draft: "Draft"
        case .pendingModeration: "In review"
        case .active: "Active"
        case .reserved: "Reserved"
        case .sold: "Sold"
        case .archived: "Archived"
        case .rejected: "Needs changes"
        case .removed: "Removed"
        }
    }
}

struct Listing: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let sellerID: UUID
    let title: String
    let description: String
    let categoryID: UUID
    let subcategoryID: UUID?
    let categoryName: String
    let subcategoryName: String?
    let priceCents: Int
    let isFree: Bool
    let condition: ListingCondition
    let status: ListingStatus
    let pickupZone: String
    let imageURL: URL?
    let publishedAt: Date?
    let viewCount: Int
    let saveCount: Int

    var formattedPrice: String {
        guard !isFree else { return "Free" }
        return (Double(priceCents) / 100).formatted(.currency(code: "USD").precision(.fractionLength(0)))
    }
}

struct ListingPage: Codable, Sendable {
    let items: [Listing]
    let total: Int
    let limit: Int
    let offset: Int
}

struct ListingFilters: Equatable, Sendable {
    var query = ""
    var category: String?
    var subcategory: String?
    var condition: ListingCondition?
    var minimumPriceCents: Int?
    var maximumPriceCents: Int?
    var freeOnly = false
    var pickupZone: String?
    var maximumAgeDays: Int?
    var sort = ListingSort.recommended
}

enum ListingSort: String, CaseIterable, Sendable {
    case recommended
    case newest
    case priceAscending = "price_asc"
    case priceDescending = "price_desc"
    case closest

    var displayName: String {
        switch self {
        case .recommended: "Recommended"
        case .newest: "Newest"
        case .priceAscending: "Price: low to high"
        case .priceDescending: "Price: high to low"
        case .closest: "Closest pickup match"
        }
    }
}
