import Foundation

enum ReservationStatus: String, Codable, Sendable {
    case active
    case completed
    case cancelled
    case expired

    var displayName: String {
        switch self {
        case .active: "Pickup needed"
        case .completed: "Completed"
        case .cancelled: "Cancelled"
        case .expired: "Expired"
        }
    }
}

struct Reservation: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let listingID: UUID
    let buyerID: UUID
    let sellerID: UUID
    let status: ReservationStatus
    let expiresAt: Date
    let createdAt: Date
}

struct ReservationRequest: Encodable, Sendable {
    let listingID: UUID
    let idempotencyKey: String
}

enum WaitlistStatus: String, Codable, Sendable {
    case waiting
    case offered
    case claimed
    case removed
}

struct WaitlistEntry: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let listingID: UUID
    let buyerID: UUID
    let status: WaitlistStatus
    let createdAt: Date
    let offerExpiresAt: Date?
}

struct Conversation: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let listingID: UUID
    let memberIDs: [UUID]
    let updatedAt: Date
}

struct ConversationRequest: Encodable, Sendable { let listingID: UUID }
struct MessageRequest: Encodable, Sendable { let body: String }

enum MessageType: String, Codable, Sendable {
    case text
    case system
}

struct YardMessage: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let conversationID: UUID
    let senderID: UUID?
    let messageType: MessageType
    let body: String
    let createdAt: Date
}

enum PickupStatus: String, Codable, Sendable {
    case proposed
    case scheduled
    case completed
    case cancelled
}

enum ArrivalStatus: String, Codable, Sendable {
    case planned
    case onTheWay = "on_the_way"
    case arrived
}

struct PickupSession: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let reservationID: UUID
    let proposedBy: UUID
    let meetingZone: String
    let proposedFor: Date
    let status: PickupStatus
    let buyerArrival: ArrivalStatus
    let sellerArrival: ArrivalStatus
    let buyerETAMinutes: Int?
    let sellerETAMinutes: Int?
    let acceptedAt: Date?
    let buyerConfirmedAt: Date?
    let sellerConfirmedAt: Date?
    let completedAt: Date?
    let cancelledAt: Date?
    let updatedAt: Date
}

struct PickupProposal: Encodable, Sendable {
    let reservationID: UUID
    let meetingZone: String
    let proposedFor: Date
}

struct PickupPresenceUpdate: Encodable, Sendable {
    let status: ArrivalStatus
    let etaMinutes: Int?
}
