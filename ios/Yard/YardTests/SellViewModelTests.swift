import Foundation
import Testing
@testable import Yard

@MainActor
struct SellViewModelTests {
    @Test
    func restoredCompleteDraftCanPublish() {
        let model = SellViewModel()
        let categoryID = UUID()
        let draft = ListingDraftRecord(
            title: "Desk lamp",
            itemDescription: "Warm adjustable reading lamp.",
            categoryID: categoryID,
            condition: .good,
            priceText: "15.00",
            isFree: false,
            pickupZone: "Harvard Square",
            photos: [DraftPhotoRecord(sortOrder: 0, data: Data([0xFF, 0xD8, 0xFF]))]
        )

        model.restore(draft)

        #expect(model.categoryID == categoryID)
        #expect(model.photos.count == 1)
        #expect(model.canPublish)
    }

    @Test
    func draftRequiresPhotoAndValidDetails() {
        let model = SellViewModel()
        model.title = "Hi"
        model.itemDescription = "Ok"
        model.categoryID = UUID()
        model.isFree = true

        #expect(!model.canPublish)
    }
}
