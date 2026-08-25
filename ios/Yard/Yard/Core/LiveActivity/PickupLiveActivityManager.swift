import ActivityKit
import Foundation

actor PickupLiveActivityManager {
    static let shared = PickupLiveActivityManager()

    private var expirationTasks: [UUID: Task<Void, Never>] = [:]

    func synchronize(_ pickup: PickupSession, reservationExpiresAt: Date) async {
        switch pickup.status {
        case .scheduled:
            await startOrUpdate(pickup, reservationExpiresAt: reservationExpiresAt)
        case .completed, .cancelled:
            await end(reservationID: pickup.reservationID, finalState: contentState(for: pickup))
        case .proposed:
            break
        }
    }

    func endExpired(reservationID: UUID) async {
        await end(
            reservationID: reservationID,
            finalState: .init(
                status: "Expired", buyerStatus: "Ended", sellerStatus: "Ended",
                buyerETAMinutes: nil, sellerETAMinutes: nil
            )
        )
    }

    private func startOrUpdate(_ pickup: PickupSession, reservationExpiresAt: Date) async {
        let state = contentState(for: pickup)
        let endDate = min(reservationExpiresAt, pickup.proposedFor.addingTimeInterval(7_200))
        let content = ActivityContent(state: state, staleDate: endDate)
        let attributes = PickupActivityAttributes(
            reservationID: pickup.reservationID,
            itemTitle: "Yard pickup",
            meetingZone: pickup.meetingZone,
            proposedFor: pickup.proposedFor
        )
        await Self.startOrUpdateActivity(attributes: attributes, content: content)
        scheduleExpiration(reservationID: pickup.reservationID, at: endDate, state: state)
    }

    private func scheduleExpiration(
        reservationID: UUID,
        at endDate: Date,
        state: PickupActivityAttributes.ContentState
    ) {
        expirationTasks[reservationID]?.cancel()
        expirationTasks[reservationID] = Task { [weak self] in
            let interval = max(0, endDate.timeIntervalSinceNow)
            try? await Task.sleep(for: .seconds(interval))
            guard !Task.isCancelled else { return }
            await self?.end(reservationID: reservationID, finalState: state)
        }
    }

    private func end(
        reservationID: UUID,
        finalState: PickupActivityAttributes.ContentState
    ) async {
        expirationTasks[reservationID]?.cancel()
        expirationTasks[reservationID] = nil
        await Self.endActivity(reservationID: reservationID, finalState: finalState)
    }

    nonisolated private static func startOrUpdateActivity(
        attributes: PickupActivityAttributes,
        content: ActivityContent<PickupActivityAttributes.ContentState>
    ) async {
        if let existing = Activity<PickupActivityAttributes>.activities.first(where: {
            $0.attributes.reservationID == attributes.reservationID
        }) {
            await existing.update(content)
        } else if ActivityAuthorizationInfo().areActivitiesEnabled {
            do {
                _ = try Activity.request(attributes: attributes, content: content, pushType: nil)
            } catch {
                // Pickup coordination remains fully functional when Live Activities are unavailable.
            }
        }
    }

    nonisolated private static func endActivity(
        reservationID: UUID,
        finalState: PickupActivityAttributes.ContentState
    ) async {
        guard let existing = Activity<PickupActivityAttributes>.activities.first(where: {
            $0.attributes.reservationID == reservationID
        }) else { return }
        await existing.end(
            ActivityContent(state: finalState, staleDate: .now),
            dismissalPolicy: .immediate
        )
    }

    private func contentState(
        for pickup: PickupSession
    ) -> PickupActivityAttributes.ContentState {
        .init(
            status: pickup.status.activityLabel,
            buyerStatus: pickup.buyerArrival.activityLabel,
            sellerStatus: pickup.sellerArrival.activityLabel,
            buyerETAMinutes: pickup.buyerETAMinutes,
            sellerETAMinutes: pickup.sellerETAMinutes
        )
    }
}

private extension PickupStatus {
    var activityLabel: String {
        switch self {
        case .proposed: "Proposed"
        case .scheduled: "Pickup scheduled"
        case .completed: "Completed"
        case .cancelled: "Cancelled"
        }
    }
}

private extension ArrivalStatus {
    var activityLabel: String {
        switch self {
        case .planned: "Planning"
        case .onTheWay: "On the way"
        case .arrived: "Arrived"
        }
    }
}
