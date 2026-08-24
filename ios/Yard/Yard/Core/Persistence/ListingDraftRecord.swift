import Foundation
import SwiftData

@Model
final class ListingDraftRecord {
    var id: UUID
    var title: String
    var itemDescription: String
    var categoryID: UUID?
    var conditionRawValue: String
    var priceText: String
    var isFree: Bool
    var pickupZone: String
    var updatedAt: Date
    @Relationship(deleteRule: .cascade) var photos: [DraftPhotoRecord]

    init(
        id: UUID = UUID(),
        title: String,
        itemDescription: String,
        categoryID: UUID?,
        condition: ListingCondition,
        priceText: String,
        isFree: Bool,
        pickupZone: String,
        photos: [DraftPhotoRecord]
    ) {
        self.id = id
        self.title = title
        self.itemDescription = itemDescription
        self.categoryID = categoryID
        self.conditionRawValue = condition.rawValue
        self.priceText = priceText
        self.isFree = isFree
        self.pickupZone = pickupZone
        self.updatedAt = .now
        self.photos = photos
    }

    var condition: ListingCondition {
        ListingCondition(rawValue: conditionRawValue) ?? .good
    }
}

@Model
final class DraftPhotoRecord {
    var id: UUID
    var sortOrder: Int
    @Attribute(.externalStorage) var data: Data

    init(id: UUID = UUID(), sortOrder: Int, data: Data) {
        self.id = id
        self.sortOrder = sortOrder
        self.data = data
    }
}
