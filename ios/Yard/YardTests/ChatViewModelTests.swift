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
}
