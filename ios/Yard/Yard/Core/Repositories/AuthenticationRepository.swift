import Foundation

protocol AuthenticationRepository: Sendable {
    func developmentSignIn() async throws -> AuthenticationResponse
    func appleSignIn(identityToken: String, displayName: String?) async throws
        -> AuthenticationResponse
    func me(accessToken: String) async throws -> YardUser
    func requestVerification(email: String, accessToken: String) async throws
        -> VerificationRequestResponse
    func confirmVerification(email: String, code: String, accessToken: String) async throws
        -> YardUser
    func redeemReviewAccess(code: String, accessToken: String) async throws -> YardUser
    func updateProfile(displayName: String, accessToken: String) async throws -> YardUser
    func deleteAccount(accessToken: String) async throws
}

actor LiveAuthenticationRepository: AuthenticationRepository {
    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    func developmentSignIn() async throws -> AuthenticationResponse {
        try await client.request(
            "POST",
            path: "api/v1/auth/development",
            body: DevelopmentSignInBody(displayName: "Alex Rivers", role: "member")
        )
    }

    func appleSignIn(
        identityToken: String, displayName: String?
    ) async throws -> AuthenticationResponse {
        try await client.request(
            "POST",
            path: "api/v1/auth/apple",
            body: AppleSignInBody(identityToken: identityToken, displayName: displayName)
        )
    }

    func me(accessToken: String) async throws -> YardUser {
        try await client.request("GET", path: "api/v1/auth/me", accessToken: accessToken)
    }

    func requestVerification(
        email: String, accessToken: String
    ) async throws -> VerificationRequestResponse {
        try await client.request(
            "POST",
            path: "api/v1/auth/verification/request",
            body: VerificationEmailBody(email: email),
            accessToken: accessToken
        )
    }

    func confirmVerification(
        email: String, code: String, accessToken: String
    ) async throws -> YardUser {
        try await client.request(
            "POST",
            path: "api/v1/auth/verification/confirm",
            body: VerificationCodeBody(email: email, code: code),
            accessToken: accessToken
        )
    }

    func redeemReviewAccess(code: String, accessToken: String) async throws -> YardUser {
        try await client.request(
            "POST",
            path: "api/v1/auth/review-access",
            body: ReviewAccessBody(code: code),
            accessToken: accessToken
        )
    }

    func updateProfile(displayName: String, accessToken: String) async throws -> YardUser {
        try await client.request(
            "PATCH",
            path: "api/v1/auth/profile",
            body: ProfileUpdateBody(displayName: displayName),
            accessToken: accessToken
        )
    }

    func deleteAccount(accessToken: String) async throws {
        try await client.requestVoid(
            "DELETE", path: "api/v1/auth/account", accessToken: accessToken
        )
    }
}

private struct DevelopmentSignInBody: Encodable, Sendable {
    let displayName: String
    let role: String
}

private struct AppleSignInBody: Encodable, Sendable {
    let identityToken: String
    let displayName: String?
}

private struct VerificationEmailBody: Encodable, Sendable {
    let email: String
}

private struct VerificationCodeBody: Encodable, Sendable {
    let email: String
    let code: String
}

private struct ReviewAccessBody: Encodable, Sendable {
    let code: String
}

private struct ProfileUpdateBody: Encodable, Sendable {
    let displayName: String
}
