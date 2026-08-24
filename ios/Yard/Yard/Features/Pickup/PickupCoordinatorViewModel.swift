import Foundation
import Observation

@MainActor
@Observable
final class PickupCoordinatorViewModel {
    private(set) var pickup: PickupSession?
    private(set) var isWorking = false
    var meetingZone = "Harvard Square"
    var proposedFor = Date.now.addingTimeInterval(3_600)
    var etaMinutes = 10
    var errorMessage: String?

    let meetingZones = [
        "Harvard Square", "Smith Campus Center area", "SEC", "Quad",
        "Lamont Library area", "Science Center Plaza",
    ]

    func load(
        reservationID: UUID,
        reservationExpiresAt: Date,
        using repository: any TransactionRepository,
        accessToken: String
    ) async {
        do {
            let loaded = try await repository.pickup(
                reservationID: reservationID, accessToken: accessToken
            )
            pickup = loaded
            await PickupLiveActivityManager.shared.synchronize(
                loaded, reservationExpiresAt: reservationExpiresAt
            )
        } catch {
            if error.transactionCode != "pickup_not_found" {
                errorMessage = error.transactionMessage
            }
        }
    }

    func propose(
        reservationID: UUID,
        using repository: any TransactionRepository,
        accessToken: String
    ) async {
        await perform {
            try await repository.proposePickup(
                PickupProposal(
                    reservationID: reservationID,
                    meetingZone: meetingZone,
                    proposedFor: proposedFor
                ),
                accessToken: accessToken
            )
        }
    }

    func accept(
        reservationID: UUID,
        reservationExpiresAt: Date,
        using repository: any TransactionRepository,
        accessToken: String
    ) async {
        await perform(reservationExpiresAt: reservationExpiresAt) {
            try await repository.acceptPickup(
                reservationID: reservationID, accessToken: accessToken
            )
        }
    }

    func updatePresence(
        _ status: ArrivalStatus,
        reservationID: UUID,
        reservationExpiresAt: Date,
        using repository: any TransactionRepository,
        accessToken: String
    ) async {
        await perform(reservationExpiresAt: reservationExpiresAt) {
            try await repository.updatePresence(
                reservationID: reservationID,
                update: PickupPresenceUpdate(
                    status: status,
                    etaMinutes: status == .onTheWay ? etaMinutes : nil
                ),
                accessToken: accessToken
            )
        }
    }

    func complete(
        reservationID: UUID,
        reservationExpiresAt: Date,
        using repository: any TransactionRepository,
        accessToken: String
    ) async {
        await perform(reservationExpiresAt: reservationExpiresAt) {
            try await repository.completePickup(
                reservationID: reservationID, accessToken: accessToken
            )
        }
    }

    func cancel(
        reservationID: UUID,
        reservationExpiresAt: Date,
        using repository: any TransactionRepository,
        accessToken: String
    ) async {
        await perform(reservationExpiresAt: reservationExpiresAt) {
            try await repository.cancelPickup(
                reservationID: reservationID, accessToken: accessToken
            )
        }
    }

    private func perform(
        reservationExpiresAt: Date? = nil,
        _ operation: () async throws -> PickupSession
    ) async {
        isWorking = true
        errorMessage = nil
        do {
            let updated = try await operation()
            pickup = updated
            if let reservationExpiresAt {
                await PickupLiveActivityManager.shared.synchronize(
                    updated, reservationExpiresAt: reservationExpiresAt
                )
            }
        }
        catch { errorMessage = error.transactionMessage }
        isWorking = false
    }
}
