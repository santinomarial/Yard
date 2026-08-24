import Foundation

protocol TransactionRepository: Sendable {
    func reserve(listingID: UUID, idempotencyKey: String, accessToken: String) async throws -> Reservation
    func joinWaitlist(listingID: UUID, accessToken: String) async throws -> WaitlistEntry
    func conversation(listingID: UUID, accessToken: String) async throws -> Conversation
    func conversations(accessToken: String) async throws -> [Conversation]
    func messages(conversationID: UUID, accessToken: String) async throws -> [YardMessage]
    func sendMessage(_ body: String, conversationID: UUID, accessToken: String) async throws -> YardMessage
    func markRead(conversationID: UUID, accessToken: String) async throws
}

actor LiveTransactionRepository: TransactionRepository {
    private let client: APIClient

    init(client: APIClient) { self.client = client }

    func reserve(listingID: UUID, idempotencyKey: String, accessToken: String) async throws -> Reservation {
        try await client.request(
            "POST",
            path: "api/v1/reservations",
            body: ReservationRequest(listingID: listingID, idempotencyKey: idempotencyKey),
            accessToken: accessToken
        )
    }

    func joinWaitlist(listingID: UUID, accessToken: String) async throws -> WaitlistEntry {
        try await client.request(
            "PUT", path: "api/v1/reservations/waitlist/\(listingID)", accessToken: accessToken
        )
    }

    func conversation(listingID: UUID, accessToken: String) async throws -> Conversation {
        try await client.request(
            "POST",
            path: "api/v1/conversations",
            body: ConversationRequest(listingID: listingID),
            accessToken: accessToken
        )
    }

    func conversations(accessToken: String) async throws -> [Conversation] {
        try await client.request(
            "GET", path: "api/v1/conversations", accessToken: accessToken
        )
    }

    func messages(conversationID: UUID, accessToken: String) async throws -> [YardMessage] {
        try await client.request(
            "GET",
            path: "api/v1/conversations/\(conversationID)/messages",
            accessToken: accessToken
        )
    }

    func sendMessage(_ body: String, conversationID: UUID, accessToken: String) async throws -> YardMessage {
        try await client.request(
            "POST",
            path: "api/v1/conversations/\(conversationID)/messages",
            body: MessageRequest(body: body),
            accessToken: accessToken
        )
    }

    func markRead(conversationID: UUID, accessToken: String) async throws {
        try await client.requestVoid(
            "POST",
            path: "api/v1/conversations/\(conversationID)/read",
            accessToken: accessToken
        )
    }
}

actor PreviewTransactionRepository: TransactionRepository {
    func reserve(listingID: UUID, idempotencyKey: String, accessToken: String) async throws -> Reservation {
        Reservation(
            id: UUID(), listingID: listingID, buyerID: UUID(), sellerID: UUID(),
            status: .active, expiresAt: .now.addingTimeInterval(1_800), createdAt: .now
        )
    }

    func joinWaitlist(listingID: UUID, accessToken: String) async throws -> WaitlistEntry {
        WaitlistEntry(
            id: UUID(), listingID: listingID, buyerID: UUID(), status: .waiting,
            createdAt: .now, offerExpiresAt: nil
        )
    }

    func conversation(listingID: UUID, accessToken: String) async throws -> Conversation {
        Conversation(id: UUID(), listingID: listingID, memberIDs: [], updatedAt: .now)
    }

    func conversations(accessToken: String) async throws -> [Conversation] { [] }
    func messages(conversationID: UUID, accessToken: String) async throws -> [YardMessage] { [] }
    func sendMessage(_ body: String, conversationID: UUID, accessToken: String) async throws -> YardMessage {
        YardMessage(
            id: UUID(), conversationID: conversationID, senderID: UUID(), messageType: .text,
            body: body, createdAt: .now
        )
    }
    func markRead(conversationID: UUID, accessToken: String) async throws {}
}
