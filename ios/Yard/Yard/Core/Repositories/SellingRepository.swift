import Foundation

protocol SellingRepository: Sendable {
    func myListings(accessToken: String) async throws -> [Listing]
    func update(
        listingID: UUID,
        priceCents: Int,
        isFree: Bool,
        condition: ListingCondition,
        pickupZone: String,
        accessToken: String
    ) async throws -> Listing
    func archive(listingID: UUID, accessToken: String) async throws -> Listing
    func relist(listingID: UUID, accessToken: String) async throws -> Listing
    func publish(
        draft: ListingDraftPayload,
        photos: [PreparedListingPhoto],
        accessToken: String,
        progress: @escaping @Sendable (Double) async -> Void
    ) async throws -> Listing
}

actor LiveSellingRepository: SellingRepository {
    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    func myListings(accessToken: String) async throws -> [Listing] {
        try await client.request("GET", path: "api/v1/listings/mine", accessToken: accessToken)
    }

    func update(
        listingID: UUID,
        priceCents: Int,
        isFree: Bool,
        condition: ListingCondition,
        pickupZone: String,
        accessToken: String
    ) async throws -> Listing {
        try await client.request(
            "PATCH",
            path: "api/v1/listings/\(listingID)",
            body: SafeListingUpdate(
                priceCents: priceCents,
                isFree: isFree,
                condition: condition,
                pickupZone: pickupZone
            ),
            accessToken: accessToken
        )
    }

    func archive(listingID: UUID, accessToken: String) async throws -> Listing {
        try await client.request(
            "POST",
            path: "api/v1/listings/\(listingID)/archive",
            accessToken: accessToken
        )
    }

    func relist(listingID: UUID, accessToken: String) async throws -> Listing {
        try await client.request(
            "POST",
            path: "api/v1/listings/\(listingID)/relist",
            accessToken: accessToken
        )
    }

    func publish(
        draft: ListingDraftPayload,
        photos: [PreparedListingPhoto],
        accessToken: String,
        progress: @escaping @Sendable (Double) async -> Void
    ) async throws -> Listing {
        let listing: Listing = try await client.request(
            "POST",
            path: "api/v1/listings",
            body: draft,
            accessToken: accessToken
        )
        let totalSteps = max(1, photos.count * 2 + 1)
        var completedSteps = 0
        for (index, photo) in photos.enumerated() {
            let upload: ListingImageUpload = try await client.request(
                "POST",
                path: "api/v1/listings/\(listing.id)/images/uploads",
                body: ListingImageUploadRequest(
                    contentType: photo.contentType,
                    byteSize: photo.data.count,
                    sortOrder: index
                ),
                accessToken: accessToken
            )
            try await client.upload(
                photo.data, to: upload.uploadURL, headers: upload.requiredHeaders
            )
            completedSteps += 1
            await progress(Double(completedSteps) / Double(totalSteps))
            let _: ListingImageRecord = try await client.request(
                "POST",
                path: "api/v1/listings/\(listing.id)/images/\(upload.image.id)/complete",
                accessToken: accessToken
            )
            completedSteps += 1
            await progress(Double(completedSteps) / Double(totalSteps))
        }
        let published: Listing = try await client.request(
            "POST",
            path: "api/v1/listings/\(listing.id)/submit",
            accessToken: accessToken
        )
        await progress(1)
        return published
    }
}

private struct SafeListingUpdate: Encodable {
    let priceCents: Int
    let isFree: Bool
    let condition: ListingCondition
    let pickupZone: String
}

actor PreviewSellingRepository: SellingRepository {
    func myListings(accessToken: String) async throws -> [Listing] { Listing.previewListings }

    func update(
        listingID: UUID,
        priceCents: Int,
        isFree: Bool,
        condition: ListingCondition,
        pickupZone: String,
        accessToken: String
    ) async throws -> Listing { Listing.previewListings[0] }

    func archive(listingID: UUID, accessToken: String) async throws -> Listing {
        Listing.previewListings[0]
    }

    func relist(listingID: UUID, accessToken: String) async throws -> Listing {
        Listing.previewListings[0]
    }

    func publish(
        draft: ListingDraftPayload,
        photos: [PreparedListingPhoto],
        accessToken: String,
        progress: @escaping @Sendable (Double) async -> Void
    ) async throws -> Listing {
        await progress(1)
        return Listing.previewListings[0]
    }
}
