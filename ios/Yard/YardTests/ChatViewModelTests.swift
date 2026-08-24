import Foundation
import Testing
@testable import Yard

@MainActor
struct ChatViewModelTests {
    @Test
    func sendingTrimsAndAppendsMessage() async {
        let repository = TransactionRepositoryStub()
        let model = ChatViewModel()
        model.draft = "  Is this available?  "

        await model.send(conversationID: UUID(), using: repository, accessToken: "token")

        #expect(model.messages.last?.body == "Is this available?")
        #expect(model.draft.isEmpty)
    }
}

private actor TransactionRepositoryStub: TransactionRepository {
    func reservations(accessToken: String) async throws -> [Reservation] { [] }
    func reserve(listingID: UUID, idempotencyKey: String, accessToken: String) async throws -> Reservation {
        fatalError()
    }
    func joinWaitlist(listingID: UUID, accessToken: String) async throws -> WaitlistEntry { fatalError() }
    func conversation(listingID: UUID, accessToken: String) async throws -> Conversation { fatalError() }
    func conversations(accessToken: String) async throws -> [Conversation] { [] }
    func messages(conversationID: UUID, accessToken: String) async throws -> [YardMessage] { [] }
    func sendMessage(_ body: String, conversationID: UUID, accessToken: String) async throws -> YardMessage {
        YardMessage(
            id: UUID(), conversationID: conversationID, senderID: UUID(), messageType: .text,
            body: body, createdAt: .now
        )
    }
    func markRead(conversationID: UUID, accessToken: String) async throws {}
    func messageStream(
        conversationID: UUID, accessToken: String
    ) async throws -> AsyncThrowingStream<YardMessage, Error> {
        AsyncThrowingStream { $0.finish() }
    }
    func pickup(reservationID: UUID, accessToken: String) async throws -> PickupSession { fatalError() }
    func proposePickup(_ proposal: PickupProposal, accessToken: String) async throws -> PickupSession { fatalError() }
    func acceptPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession { fatalError() }
    func updatePresence(
        reservationID: UUID, update: PickupPresenceUpdate, accessToken: String
    ) async throws -> PickupSession { fatalError() }
    func completePickup(reservationID: UUID, accessToken: String) async throws -> PickupSession { fatalError() }
    func cancelPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession { fatalError() }
}
