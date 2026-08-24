import Foundation

protocol NotificationRepository: Sendable {
    func registerDevice(token: String, environment: String, accessToken: String) async throws
        -> DeviceRegistration
    func revokeDevice(id: UUID, accessToken: String) async throws
    func notifications(accessToken: String) async throws -> [YardNotification]
}

actor LiveNotificationRepository: NotificationRepository {
    private let client: APIClient

    init(client: APIClient) { self.client = client }

    func registerDevice(
        token: String, environment: String, accessToken: String
    ) async throws -> DeviceRegistration {
        try await client.request(
            "POST",
            path: "api/v1/notifications/devices",
            body: DeviceRegistrationRequest(token: token, environment: environment),
            accessToken: accessToken
        )
    }

    func revokeDevice(id: UUID, accessToken: String) async throws {
        try await client.requestVoid(
            "DELETE", path: "api/v1/notifications/devices/\(id)", accessToken: accessToken
        )
    }

    func notifications(accessToken: String) async throws -> [YardNotification] {
        try await client.request(
            "GET", path: "api/v1/notifications", accessToken: accessToken
        )
    }
}

struct PreviewNotificationRepository: NotificationRepository {
    func registerDevice(
        token: String, environment: String, accessToken: String
    ) async throws -> DeviceRegistration {
        DeviceRegistration(id: UUID(), environment: environment, createdAt: .now)
    }
    func revokeDevice(id: UUID, accessToken: String) async throws {}
    func notifications(accessToken: String) async throws -> [YardNotification] { [] }
}

private struct DeviceRegistrationRequest: Encodable, Sendable {
    let token: String
    let environment: String
}
