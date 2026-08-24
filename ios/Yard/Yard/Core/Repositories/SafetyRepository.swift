import Foundation

protocol SafetyRepository: Sendable {
    func report(_ submission: ReportSubmission, accessToken: String) async throws
    func block(userID: UUID, accessToken: String) async throws
}

actor LiveSafetyRepository: SafetyRepository {
    private let client: APIClient

    init(client: APIClient) { self.client = client }

    func report(_ submission: ReportSubmission, accessToken: String) async throws {
        try await client.requestVoid(
            "POST", path: "api/v1/reports", body: submission, accessToken: accessToken
        )
    }

    func block(userID: UUID, accessToken: String) async throws {
        try await client.requestVoid(
            "PUT", path: "api/v1/blocks/\(userID)", accessToken: accessToken
        )
    }
}

struct PreviewSafetyRepository: SafetyRepository {
    func report(_ submission: ReportSubmission, accessToken: String) async throws {}
    func block(userID: UUID, accessToken: String) async throws {}
}
