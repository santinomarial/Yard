import Foundation

protocol BuyerRepository: Sendable {
    func savedListings(accessToken: String) async throws -> [Listing]
    func setSaved(_ saved: Bool, listingID: UUID, accessToken: String) async throws
    func intents(accessToken: String) async throws -> [BuyingIntent]
    func createIntent(_ draft: BuyingIntentDraft, accessToken: String) async throws -> BuyingIntent
    func matches(intentID: UUID, accessToken: String) async throws -> [ListingMatch]
}

actor LiveBuyerRepository: BuyerRepository {
    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    func savedListings(accessToken: String) async throws -> [Listing] {
        try await client.request("GET", path: "api/v1/buyer/saved", accessToken: accessToken)
    }

    func setSaved(_ saved: Bool, listingID: UUID, accessToken: String) async throws {
        try await client.requestVoid(
            saved ? "PUT" : "DELETE",
            path: "api/v1/buyer/saved/\(listingID)",
            accessToken: accessToken
        )
    }

    func intents(accessToken: String) async throws -> [BuyingIntent] {
        try await client.request("GET", path: "api/v1/buyer/intents", accessToken: accessToken)
    }

    func createIntent(_ draft: BuyingIntentDraft, accessToken: String) async throws -> BuyingIntent {
        try await client.request(
            "POST", path: "api/v1/buyer/intents", body: draft, accessToken: accessToken
        )
    }

    func matches(intentID: UUID, accessToken: String) async throws -> [ListingMatch] {
        try await client.request(
            "GET", path: "api/v1/buyer/intents/\(intentID)/matches", accessToken: accessToken
        )
    }
}

actor PreviewBuyerRepository: BuyerRepository {
    private var saved = Listing.previewListings

    func savedListings(accessToken: String) async throws -> [Listing] { saved }

    func setSaved(_ isSaved: Bool, listingID: UUID, accessToken: String) async throws {
        if isSaved, let listing = Listing.previewListings.first(where: { $0.id == listingID }) {
            if !saved.contains(listing) { saved.append(listing) }
        } else if !isSaved {
            saved.removeAll { $0.id == listingID }
        }
    }

    func intents(accessToken: String) async throws -> [BuyingIntent] { [] }

    func createIntent(_ draft: BuyingIntentDraft, accessToken: String) async throws -> BuyingIntent {
        BuyingIntent(
            id: UUID(), buyerID: UUID(), query: draft.query, categoryID: draft.categoryID,
            maximumPriceCents: draft.maximumPriceCents,
            minimumCondition: draft.minimumCondition, pickupZone: draft.pickupZone,
            isActive: true, createdAt: .now
        )
    }

    func matches(intentID: UUID, accessToken: String) async throws -> [ListingMatch] {
        Listing.previewListings.map {
            ListingMatch(id: UUID(), score: 0.85, scoreComponents: ["text": 0.85], listing: $0)
        }
    }
}
