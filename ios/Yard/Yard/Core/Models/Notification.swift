import Foundation

struct DeviceRegistration: Codable, Identifiable, Sendable {
    let id: UUID
    let environment: String
    let createdAt: Date
}

enum NotificationDeliveryStatus: String, Codable, Sendable {
    case pending
    case sent
    case failed
}

struct YardNotification: Codable, Identifiable, Sendable {
    let id: UUID
    let notificationType: String
    let title: String
    let body: String
    let deepLink: URL?
    let data: [String: JSONValue]
    let status: NotificationDeliveryStatus
    let sentAt: Date?
    let createdAt: Date
}

enum JSONValue: Codable, Sendable {
    case string(String)
    case number(Double)
    case boolean(Bool)
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() { self = .null }
        else if let value = try? container.decode(Bool.self) { self = .boolean(value) }
        else if let value = try? container.decode(Double.self) { self = .number(value) }
        else { self = .string(try container.decode(String.self)) }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case let .string(value): try container.encode(value)
        case let .number(value): try container.encode(value)
        case let .boolean(value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }
}
