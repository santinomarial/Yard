import Foundation

enum MarketplaceAccessMethod: String, Codable, Sendable {
    case none
    case harvardEmail = "harvard_email"
    case appReview = "app_review"
}

struct YardUser: Codable, Equatable, Sendable {
    let id: UUID
    let displayName: String
    let harvardEmailVerified: Bool
    let marketplaceAccessGranted: Bool
    let accessMethod: MarketplaceAccessMethod
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
