import Foundation
import Observation

@MainActor
@Observable
final class ChatViewModel {
    private(set) var messages: [YardMessage] = []
    private(set) var isLoading = true
    private(set) var isSending = false
    var draft = ""
    var errorMessage: String?

    func load(
        conversationID: UUID,
        using repository: any TransactionRepository,
        accessToken: String
    ) async {
        isLoading = true
        do {
            messages = try await repository.messages(
                conversationID: conversationID, accessToken: accessToken
            )
            try? await repository.markRead(
                conversationID: conversationID, accessToken: accessToken
            )
        } catch {
            errorMessage = error.transactionMessage
        }
        isLoading = false
    }

    func send(
        conversationID: UUID,
        using repository: any TransactionRepository,
        accessToken: String
    ) async {
        let body = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty, body.count <= 2_000 else { return }
        isSending = true
        errorMessage = nil
        do {
            let message = try await repository.sendMessage(
                body, conversationID: conversationID, accessToken: accessToken
            )
            messages.append(message)
            draft = ""
        } catch {
            errorMessage = error.transactionMessage
        }
        isSending = false
    }
}

extension Error {
    var transactionMessage: String {
        if let error = self as? APIError,
           case let .rejected(_, _, message) = error { return message }
        return "Yard could not complete that action. Check your connection and try again."
    }

    var transactionCode: String? {
        if let error = self as? APIError,
           case let .rejected(_, code, _) = error { return code }
        return nil
    }
}
