import Foundation
import SwiftData

@Model
final class CachedListingRecord {
    @Attribute(.unique) var id: UUID
    @Attribute(.externalStorage) var payload: Data
    var cachedAt: Date

    init(id: UUID, payload: Data, cachedAt: Date = .now) {
        self.id = id
        self.payload = payload
        self.cachedAt = cachedAt
    }
}

@Model
final class CachedCategoryRecord {
    @Attribute(.unique) var id: UUID
    @Attribute(.externalStorage) var payload: Data
    var cachedAt: Date

    init(id: UUID, payload: Data, cachedAt: Date = .now) {
        self.id = id
        self.payload = payload
        self.cachedAt = cachedAt
    }
}

@Model
final class FavoriteRecord {
    @Attribute(.unique) var listingID: UUID
    @Attribute(.externalStorage) var listingPayload: Data
    var savedAt: Date

    init(listingID: UUID, listingPayload: Data, savedAt: Date = .now) {
        self.listingID = listingID
        self.listingPayload = listingPayload
        self.savedAt = savedAt
    }
}

@Model
final class PendingFavoriteMutation {
    @Attribute(.unique) var listingID: UUID
    var isSaved: Bool
    var updatedAt: Date

    init(listingID: UUID, isSaved: Bool, updatedAt: Date = .now) {
        self.listingID = listingID
        self.isSaved = isSaved
        self.updatedAt = updatedAt
    }
}

@Model
final class CachedConversationRecord {
    @Attribute(.unique) var id: UUID
    @Attribute(.externalStorage) var payload: Data
    var cachedAt: Date

    init(id: UUID, payload: Data, cachedAt: Date = .now) {
        self.id = id
        self.payload = payload
        self.cachedAt = cachedAt
    }
}
