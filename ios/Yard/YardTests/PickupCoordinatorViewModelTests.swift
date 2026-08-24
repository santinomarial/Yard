import Foundation
import Testing
@testable import Yard

@MainActor
struct PickupCoordinatorViewModelTests {
    @Test
    func missingPickupIsAnEmptyCoordinationState() async {
        let model = PickupCoordinatorViewModel()

        await model.load(
            reservationID: UUID(), using: PickupRepositoryStub(), accessToken: "token"
        )

        #expect(model.pickup == nil)
        #expect(model.errorMessage == nil)
    }
}

private actor PickupRepositoryStub: TransactionRepository {
    func reservations(accessToken: String) async throws -> [Reservation] { [] }
    func reserve(listingID: UUID, idempotencyKey: String, accessToken: String) async throws -> Reservation { fatalError() }
    func joinWaitlist(listingID: UUID, accessToken: String) async throws -> WaitlistEntry { fatalError() }
    func conversation(listingID: UUID, accessToken: String) async throws -> Conversation { fatalError() }
    func conversations(accessToken: String) async throws -> [Conversation] { [] }
    func messages(conversationID: UUID, accessToken: String) async throws -> [YardMessage] { [] }
    func sendMessage(_ body: String, conversationID: UUID, accessToken: String) async throws -> YardMessage { fatalError() }
    func markRead(conversationID: UUID, accessToken: String) async throws {}
    func messageStream(
        conversationID: UUID, accessToken: String
    ) async throws -> AsyncThrowingStream<YardMessage, Error> {
        AsyncThrowingStream { $0.finish() }
    }
    func pickup(reservationID: UUID, accessToken: String) async throws -> PickupSession {
        throw APIError.rejected(statusCode: 404, code: "pickup_not_found", message: "Not found")
    }
    func proposePickup(_ proposal: PickupProposal, accessToken: String) async throws -> PickupSession { fatalError() }
    func acceptPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession { fatalError() }
    func updatePresence(
        reservationID: UUID, update: PickupPresenceUpdate, accessToken: String
    ) async throws -> PickupSession { fatalError() }
    func completePickup(reservationID: UUID, accessToken: String) async throws -> PickupSession { fatalError() }
    func cancelPickup(reservationID: UUID, accessToken: String) async throws -> PickupSession { fatalError() }
}
