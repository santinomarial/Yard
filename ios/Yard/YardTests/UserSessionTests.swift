import Foundation
import Testing
@testable import Yard

@MainActor
struct UserSessionTests {
    @Test
    func restoresPersistedSession() async {
        let store = RecordingTokenStore(token: "saved-token")
        let repository = StubAuthenticationRepository()
        let session = UserSession(repository: repository, tokenStore: store)

        await session.restore()

        #expect(session.accessToken == "saved-token")
        #expect(session.phase == .signedIn(repository.user))
    }

    @Test
    func developmentSignInPersistsToken() async {
        let store = RecordingTokenStore()
        let repository = StubAuthenticationRepository()
        let session = UserSession(
            repository: repository,
            tokenStore: store,
            initialPhase: .signedOut
        )

        await session.signInForDevelopment()

        #expect(store.token == "test-token")
        #expect(session.phase == .signedIn(repository.user))
    }

    @Test
    func accountDeletionClearsLocalCredentials() async {
        let store = RecordingTokenStore(token: "saved-token")
        let repository = StubAuthenticationRepository()
        let session = UserSession(repository: repository, tokenStore: store)
        await session.restore()

        let deleted = await session.deleteAccount()

        #expect(deleted)
        #expect(store.token == nil)
        #expect(session.phase == .signedOut)
    }
}

private final class RecordingTokenStore: TokenStore, @unchecked Sendable {
    var token: String?

    init(token: String? = nil) {
        self.token = token
    }

    func load() -> String? { token }
    func save(_ token: String) throws { self.token = token }
    func clear() throws { token = nil }
}

private struct StubAuthenticationRepository: AuthenticationRepository {
    let user = YardUser(
        id: UUID(uuidString: "DE229658-E8AA-4F19-9908-105458FBF009")!,
        displayName: "Test Member",
        harvardEmailVerified: true,
        memberSince: .now,
        suspended: false,
        admin: false
    )

    func developmentSignIn() async throws -> AuthenticationResponse {
        AuthenticationResponse(accessToken: "test-token", tokenType: "bearer", user: user)
    }

    func appleSignIn(
        identityToken: String, displayName: String?
    ) async throws -> AuthenticationResponse {
        AuthenticationResponse(accessToken: "test-token", tokenType: "bearer", user: user)
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

    func updateProfile(displayName: String, accessToken: String) async throws -> YardUser {
        YardUser(
            id: user.id, displayName: displayName,
            harvardEmailVerified: user.harvardEmailVerified,
            memberSince: user.memberSince, suspended: false, admin: false
        )
    }

    func deleteAccount(accessToken: String) async throws {}
}
