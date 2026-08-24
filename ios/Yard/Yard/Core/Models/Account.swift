import Foundation

struct YardUser: Codable, Equatable, Sendable {
    let id: UUID
    let displayName: String
    let harvardEmailVerified: Bool
    let memberSince: Date
    let suspended: Bool
    let admin: Bool
}

struct AuthenticationResponse: Codable, Sendable {
    let accessToken: String
    let tokenType: String
    let user: YardUser
}

struct VerificationRequestResponse: Codable, Sendable {
    let accepted: Bool
    let developmentCode: String?
}
