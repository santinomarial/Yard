import Foundation
import SwiftData

@MainActor
enum MarketplaceLocalStore {
    static func cachedMarketplace(
        context: ModelContext
    ) -> (listings: [Listing], categories: [YardCategory]) {
        let listingRecords = (try? context.fetch(FetchDescriptor<CachedListingRecord>())) ?? []
        let categoryRecords = (try? context.fetch(FetchDescriptor<CachedCategoryRecord>())) ?? []
        return (
            listingRecords.compactMap { try? JSONDecoder.yard.decode(Listing.self, from: $0.payload) },
            categoryRecords.compactMap {
                try? JSONDecoder.yard.decode(YardCategory.self, from: $0.payload)
            }
        )
    }

    static func replaceMarketplace(
        listings: [Listing], categories: [YardCategory], context: ModelContext
    ) {
        ((try? context.fetch(FetchDescriptor<CachedListingRecord>())) ?? []).forEach(context.delete)
        ((try? context.fetch(FetchDescriptor<CachedCategoryRecord>())) ?? []).forEach(context.delete)
        for listing in listings {
            if let data = try? JSONEncoder.yard.encode(listing) {
                context.insert(CachedListingRecord(id: listing.id, payload: data))
            }
        }
        for category in categories {
            if let data = try? JSONEncoder.yard.encode(category) {
                context.insert(CachedCategoryRecord(id: category.id, payload: data))
            }
        }
        try? context.save()
    }

    static func cachedFavorites(context: ModelContext) -> [Listing] {
        let records = (try? context.fetch(FetchDescriptor<FavoriteRecord>())) ?? []
        return records
            .sorted { $0.savedAt > $1.savedAt }
            .compactMap { try? JSONDecoder.yard.decode(Listing.self, from: $0.listingPayload) }
    }

    static func replaceFavorites(_ listings: [Listing], context: ModelContext) {
        ((try? context.fetch(FetchDescriptor<FavoriteRecord>())) ?? []).forEach(context.delete)
        for listing in listings {
            if let data = try? JSONEncoder.yard.encode(listing) {
                context.insert(FavoriteRecord(listingID: listing.id, listingPayload: data))
            }
        }
        try? context.save()
    }

    static func setFavorite(
        _ isSaved: Bool,
        listing: Listing,
        queueForSync: Bool,
        context: ModelContext
    ) {
        let favorites = (try? context.fetch(FetchDescriptor<FavoriteRecord>())) ?? []
        favorites.filter { $0.listingID == listing.id }.forEach(context.delete)
        if isSaved, let data = try? JSONEncoder.yard.encode(listing) {
            context.insert(FavoriteRecord(listingID: listing.id, listingPayload: data))
        }
        if queueForSync {
            let pending = (try? context.fetch(FetchDescriptor<PendingFavoriteMutation>())) ?? []
            if let existing = pending.first(where: { $0.listingID == listing.id }) {
                existing.isSaved = isSaved
                existing.updatedAt = .now
            } else {
                context.insert(PendingFavoriteMutation(listingID: listing.id, isSaved: isSaved))
            }
        }
        try? context.save()
    }

    static func syncPendingFavorites(
        context: ModelContext,
        repository: any BuyerRepository,
        accessToken: String
    ) async {
        let pending = ((try? context.fetch(FetchDescriptor<PendingFavoriteMutation>())) ?? [])
            .sorted { $0.updatedAt < $1.updatedAt }
        for mutation in pending {
            do {
                try await repository.setSaved(
                    mutation.isSaved,
                    listingID: mutation.listingID,
                    accessToken: accessToken
                )
                context.delete(mutation)
                try? context.save()
            } catch {
                return
            }
        }
    }

    static func cachedConversations(context: ModelContext) -> [Conversation] {
        let records = (try? context.fetch(FetchDescriptor<CachedConversationRecord>())) ?? []
        return records.compactMap {
            try? JSONDecoder.yard.decode(Conversation.self, from: $0.payload)
        }
    }

    static func replaceConversations(_ values: [Conversation], context: ModelContext) {
        ((try? context.fetch(FetchDescriptor<CachedConversationRecord>())) ?? [])
            .forEach(context.delete)
        for value in values {
            if let data = try? JSONEncoder.yard.encode(value) {
                context.insert(CachedConversationRecord(id: value.id, payload: data))
            }
        }
        try? context.save()
    }
}
