import Foundation
import Testing
@testable import Yard

struct ModelDecodingTests {
    @Test
    func decodesListingContract() throws {
        let json = #"""
        {
          "id": "11408445-3907-55c2-848e-8ad314eb1c7b",
          "seller_id": "67f936cf-c018-5ebf-94b5-59bf099885f3",
          "title": "Dell 27-inch Monitor",
          "description": "A sharp second screen.",
          "category_id": "c749ad33-4a65-582d-a294-c30305647020",
          "subcategory_id": null,
          "category_name": "Electronics",
          "subcategory_name": "Monitors",
          "price_cents": 8500,
          "is_free": false,
          "condition": "good",
          "status": "active",
          "pickup_zone": "Kirkland House area",
          "image_url": null,
          "published_at": "2026-08-24T05:50:17Z",
          "view_count": 3,
          "save_count": 2,
          "seller": {
            "display_name": "Maya Chen",
            "harvard_email_verified": true,
            "member_since": "2026-01-12T05:50:17Z",
            "completed_exchanges": 14
          }
        }
        """#.data(using: .utf8)!

        let listing = try JSONDecoder.yard.decode(Listing.self, from: json)

        #expect(listing.title == "Dell 27-inch Monitor")
        #expect(listing.formattedPrice == "$85")
        #expect(listing.condition == .good)
        #expect(listing.seller?.displayName == "Maya Chen")
        #expect(listing.seller?.completedExchanges == 14)
    }

    @Test
    func freeListingUsesClearPriceLabel() throws {
        let listing = Listing(
            id: UUID(),
            sellerID: UUID(),
            title: "Floor Lamp",
            description: "Works well.",
            categoryID: UUID(),
            subcategoryID: nil,
            categoryName: "Free",
            subcategoryName: nil,
            priceCents: 0,
            isFree: true,
            condition: .good,
            status: .active,
            pickupZone: "Harvard Square",
            imageURL: nil,
            publishedAt: nil,
            viewCount: 0,
            saveCount: 0
        )

        #expect(listing.formattedPrice == "Free")
    }
}
