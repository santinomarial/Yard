import Foundation
import Observation

enum SessionPhase: Equatable {
    case restoring
    case signedOut
    case signedIn(YardUser)
}

@MainActor
@Observable
final class UserSession {
    private let repository: any AuthenticationRepository
    private let tokenStore: any TokenStore
    private(set) var phase: SessionPhase
    private(set) var accessToken: String?
    private(set) var isWorking = false
    private(set) var errorMessage: String?
    private(set) var developmentCode: String?

    var currentUser: YardUser? {
        guard case let .signedIn(user) = phase else { return nil }
        return user
    }

    init(
        repository: any AuthenticationRepository,
        tokenStore: any TokenStore,
        initialPhase: SessionPhase = .restoring
    ) {
        self.repository = repository
        self.tokenStore = tokenStore
        self.phase = initialPhase
    }

    func restore() async {
        guard phase == .restoring else { return }
        guard let token = tokenStore.load() else {
            phase = .signedOut
            return
        }
        do {
            let user = try await repository.me(accessToken: token)
            accessToken = token
            phase = .signedIn(user)
        } catch {
            try? tokenStore.clear()
            accessToken = nil
            phase = .signedOut
        }
    }

    func signInWithApple(identityToken: String, displayName: String?) async {
        await authenticate {
            try await repository.appleSignIn(
                identityToken: identityToken,
                displayName: displayName
            )
        }
    }

    func signInForDevelopment() async {
        await authenticate { try await repository.developmentSignIn() }
    }

    func requestVerification(email: String) async {
        guard let accessToken else { return }
        isWorking = true
        errorMessage = nil
        do {
            let response = try await repository.requestVerification(
                email: email, accessToken: accessToken
            )
            developmentCode = response.developmentCode
        } catch {
            errorMessage = error.userFacingMessage
        }
        isWorking = false
    }

    func confirmVerification(email: String, code: String) async {
        guard let accessToken else { return }
        isWorking = true
        errorMessage = nil
        do {
            let user = try await repository.confirmVerification(
                email: email, code: code, accessToken: accessToken
            )
            developmentCode = nil
            phase = .signedIn(user)
        } catch {
            errorMessage = error.userFacingMessage
        }
        isWorking = false
    }

    func redeemReviewAccess(code: String) async {
        guard let accessToken else { return }
        isWorking = true
        errorMessage = nil
        do {
            let user = try await repository.redeemReviewAccess(
                code: code.trimmingCharacters(in: .whitespacesAndNewlines),
                accessToken: accessToken
            )
            phase = .signedIn(user)
        } catch {
            errorMessage = error.userFacingMessage
        }
        isWorking = false
    }

    func signOut() {
        try? tokenStore.clear()
        accessToken = nil
        developmentCode = nil
        errorMessage = nil
        phase = .signedOut
    }

    func updateProfile(displayName: String) async -> Bool {
        guard let accessToken else { return false }
        isWorking = true
        errorMessage = nil
        do {
            let user = try await repository.updateProfile(
                displayName: displayName, accessToken: accessToken
            )
            phase = .signedIn(user)
            isWorking = false
            return true
        } catch {
            errorMessage = error.userFacingMessage
            isWorking = false
            return false
        }
    }

    func deleteAccount() async -> Bool {
        guard let accessToken else { return false }
        isWorking = true
        errorMessage = nil
        do {
            try await repository.deleteAccount(accessToken: accessToken)
            signOut()
            isWorking = false
            return true
        } catch {
            errorMessage = error.userFacingMessage
            isWorking = false
            return false
        }
    }

    func clearError() {
        errorMessage = nil
    }

    private func authenticate(
        _ operation: () async throws -> AuthenticationResponse
    ) async {
        isWorking = true
        errorMessage = nil
        do {
            let response = try await operation()
            try tokenStore.save(response.accessToken)
            accessToken = response.accessToken
            phase = .signedIn(response.user)
        } catch {
            errorMessage = error.userFacingMessage
        }
        isWorking = false
    }
}

private extension Error {
    var userFacingMessage: String {
        if let apiError = self as? APIError,
           case let .rejected(_, _, message) = apiError {
            return message
        }
        if self is CancellationError { return "The request was cancelled." }
        return "Yard could not connect. Check your connection and try again."
    }
}
