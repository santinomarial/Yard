import Foundation

struct BuyingIntentDraft: Encodable, Sendable {
    let query: String
    let categoryID: UUID?
    let maximumPriceCents: Int?
    let minimumCondition: ListingCondition?
    let pickupZone: String?
}

struct BuyingIntent: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let buyerID: UUID
    let query: String
    let categoryID: UUID?
    let maximumPriceCents: Int?
    let minimumCondition: ListingCondition?
    let pickupZone: String?
    let isActive: Bool
    let createdAt: Date

    var summary: String {
        var details: [String] = []
        if let maximumPriceCents {
            details.append("up to \((Double(maximumPriceCents) / 100).formatted(.currency(code: "USD")))")
        }
        if let minimumCondition { details.append(minimumCondition.displayName) }
        if let pickupZone { details.append(pickupZone) }
        return details.isEmpty ? "Any matching item" : details.joined(separator: " · ")
    }
}

struct ListingMatch: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let score: Double
    let scoreComponents: [String: Double]
    let listing: Listing
}

struct ListingRecommendation: Codable, Identifiable, Hashable, Sendable {
    var id: UUID { listing.id }
    let score: Double
    let reasons: [String]
    let listing: Listing
}
