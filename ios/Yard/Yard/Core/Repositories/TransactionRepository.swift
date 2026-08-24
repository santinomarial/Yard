import Foundation

protocol TransactionRepository: Sendable {
    func reservations(accessToken: String) async throws -> [Reservation]
    func reserve(listingID: UUID, idempotencyKey: String, accessToken: String) async throws -> Reservation
    func joinWaitlist(listingID: UUID, accessToken: String) async throws -> WaitlistEntry
    func conversation(listingID: UUID, accessToken: String) async throws -> Conversation
    func conversations(accessToken: String) async throws -> [Conversation]
    func messages(conversationID: UUID, accessToken: String) async throws -> [YardMessage]
    func sendMessage(_ body: String, conversationID: UUID, accessToken: String) async throws -> YardMessage
    func markRead(conversationID: UUID, accessToken: String) async throws
    func pickup(reservationID: UUID, accessToken: String) async throws -> PickupSession
    func proposePickup(_ proposal: PickupProposal, accessToken: String) async throws -> PickupSession
    func acceptPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession
    func updatePresence(
        reservationID: UUID, update: PickupPresenceUpdate, accessToken: String
    ) async throws -> PickupSession
    func completePickup(reservationID: UUID, accessToken: String) async throws -> PickupSession
    func cancelPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession
}

actor LiveTransactionRepository: TransactionRepository {
    private let client: APIClient

    init(client: APIClient) { self.client = client }

    func reservations(accessToken: String) async throws -> [Reservation] {
        try await client.request(
            "GET", path: "api/v1/reservations/mine", accessToken: accessToken
        )
    }

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

    func pickup(reservationID: UUID, accessToken: String) async throws -> PickupSession {
        try await client.request(
            "GET", path: "api/v1/pickups/\(reservationID)", accessToken: accessToken
        )
    }

    func proposePickup(_ proposal: PickupProposal, accessToken: String) async throws -> PickupSession {
        try await client.request(
            "POST", path: "api/v1/pickups", body: proposal, accessToken: accessToken
        )
    }

    func acceptPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession {
        try await client.request(
            "POST", path: "api/v1/pickups/\(reservationID)/accept", accessToken: accessToken
        )
    }

    func updatePresence(
        reservationID: UUID, update: PickupPresenceUpdate, accessToken: String
    ) async throws -> PickupSession {
        try await client.request(
            "PATCH", path: "api/v1/pickups/\(reservationID)/presence",
            body: update, accessToken: accessToken
        )
    }

    func completePickup(reservationID: UUID, accessToken: String) async throws -> PickupSession {
        try await client.request(
            "POST", path: "api/v1/pickups/\(reservationID)/complete", accessToken: accessToken
        )
    }

    func cancelPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession {
        try await client.request(
            "POST", path: "api/v1/pickups/\(reservationID)/cancel", accessToken: accessToken
        )
    }
}

actor PreviewTransactionRepository: TransactionRepository {
    func reservations(accessToken: String) async throws -> [Reservation] { [] }
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

    func pickup(reservationID: UUID, accessToken: String) async throws -> PickupSession {
        throw APIError.rejected(statusCode: 404, code: "pickup_not_found", message: "Not found")
    }
    func proposePickup(_ proposal: PickupProposal, accessToken: String) async throws -> PickupSession {
        PickupSession.preview(reservationID: proposal.reservationID, zone: proposal.meetingZone, date: proposal.proposedFor)
    }
    func acceptPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession {
        PickupSession.preview(reservationID: reservationID, status: .scheduled)
    }
    func updatePresence(
        reservationID: UUID, update: PickupPresenceUpdate, accessToken: String
    ) async throws -> PickupSession {
        PickupSession.preview(reservationID: reservationID, status: .scheduled)
    }
    func completePickup(reservationID: UUID, accessToken: String) async throws -> PickupSession {
        PickupSession.preview(reservationID: reservationID, status: .completed)
    }
    func cancelPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession {
        PickupSession.preview(reservationID: reservationID, status: .cancelled)
    }
}

private extension PickupSession {
    static func preview(
        reservationID: UUID,
        zone: String = "Harvard Square",
        date: Date = .now.addingTimeInterval(3_600),
        status: PickupStatus = .proposed
    ) -> PickupSession {
        PickupSession(
            id: UUID(), reservationID: reservationID, proposedBy: UUID(),
            meetingZone: zone, proposedFor: date, status: status,
            buyerArrival: .planned, sellerArrival: .planned,
            buyerETAMinutes: nil, sellerETAMinutes: nil, acceptedAt: nil,
            buyerConfirmedAt: nil, sellerConfirmedAt: nil,
            completedAt: status == .completed ? .now : nil, cancelledAt: nil, updatedAt: .now
        )
    }
}
