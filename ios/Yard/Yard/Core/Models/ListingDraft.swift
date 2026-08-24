import Foundation

struct ListingDraftPayload: Encodable, Sendable {
    let title: String
    let description: String
    let categoryID: UUID
    let subcategoryID: UUID?
    let priceCents: Int
    let isFree: Bool
    let condition: ListingCondition
    let pickupZone: String
}

struct ListingImageUploadRequest: Encodable, Sendable {
    let contentType: String
    let byteSize: Int
    let sortOrder: Int
}

enum ListingImageStatus: String, Codable, Sendable {
    case pendingUpload = "pending_upload"
    case pendingModeration = "pending_moderation"
    case approved
    case rejected
}

struct ListingImageRecord: Codable, Identifiable, Sendable {
    let id: UUID
    let contentType: String
    let byteSize: Int
    let sortOrder: Int
    let status: ListingImageStatus
    let url: URL?
    let moderationReasons: [String]
    let uploadedAt: Date?
}

struct ListingImageUpload: Codable, Sendable {
    let image: ListingImageRecord
    let uploadURL: URL
    let requiredHeaders: [String: String]
    let expiresInSeconds: Int
}

struct PreparedListingPhoto: Identifiable, Hashable, Sendable {
    let id: UUID
    let data: Data
    let contentType: String

    init(id: UUID = UUID(), data: Data, contentType: String = "image/jpeg") {
        self.id = id
        self.data = data
        self.contentType = contentType
    }
}
