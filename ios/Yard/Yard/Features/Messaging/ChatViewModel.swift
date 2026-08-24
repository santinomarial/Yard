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
    @ObservationIgnored private var streamTask: Task<Void, Never>?

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

    func connect(
        conversationID: UUID,
        using repository: any TransactionRepository,
        accessToken: String
    ) {
        streamTask?.cancel()
        streamTask = Task { [weak self] in
            do {
                let stream = try await repository.messageStream(
                    conversationID: conversationID, accessToken: accessToken
                )
                for try await message in stream {
                    guard !Task.isCancelled else { return }
                    if self?.messages.contains(where: { $0.id == message.id }) == false {
                        self?.messages.append(message)
                    }
                }
            } catch is CancellationError {
                return
            } catch {
                guard !Task.isCancelled else { return }
                self?.errorMessage = "Live updates paused. Pull to refresh the conversation."
            }
        }
    }

    func disconnect() {
        streamTask?.cancel()
        streamTask = nil
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
