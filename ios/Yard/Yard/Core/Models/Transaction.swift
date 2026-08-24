import Foundation

enum ReservationStatus: String, Codable, Sendable {
    case active
    case completed
    case cancelled
    case expired
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
