import ActivityKit
import Foundation

struct PickupActivityAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        let status: String
        let buyerStatus: String
        let sellerStatus: String
        let buyerETAMinutes: Int?
        let sellerETAMinutes: Int?
    }

    let reservationID: UUID
    let itemTitle: String
    let meetingZone: String
    let proposedFor: Date
}
