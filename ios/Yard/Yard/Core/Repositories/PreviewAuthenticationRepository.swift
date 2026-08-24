import Foundation

struct PreviewAuthenticationRepository: AuthenticationRepository {
    let user = YardUser(
        id: UUID(uuidString: "8F5A225D-0208-4AC1-A01C-B86E0FE88DD8")!,
        displayName: "Alex Rivers",
        harvardEmailVerified: true,
        memberSince: .now,
        suspended: false,
        admin: false
    )

    func developmentSignIn() async throws -> AuthenticationResponse {
        AuthenticationResponse(accessToken: "preview", tokenType: "bearer", user: user)
    }

    func appleSignIn(
        identityToken: String, displayName: String?
    ) async throws -> AuthenticationResponse {
        AuthenticationResponse(accessToken: "preview", tokenType: "bearer", user: user)
    }

    func me(accessToken: String) async throws -> YardUser { user }

    func requestVerification(
        email: String, accessToken: String
    ) async throws -> VerificationRequestResponse {
        VerificationRequestResponse(accepted: true, developmentCode: "123456")
    }

    func confirmVerification(
        email: String, code: String, accessToken: String
    ) async throws -> YardUser { user }
}
