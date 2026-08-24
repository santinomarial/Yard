import Foundation
import Observation

@MainActor
@Observable
final class ProfileViewModel {
    private(set) var listings: [Listing] = []
    private(set) var conversations: [Conversation] = []
    private(set) var reservations: [Reservation] = []
    private(set) var isLoading = true
    var errorMessage: String?

    func restoreCachedConversations(_ conversations: [Conversation]) {
        guard self.conversations.isEmpty else { return }
        self.conversations = conversations
    }

    func load(
        selling: any SellingRepository,
        transactions: any TransactionRepository,
        accessToken: String
    ) async {
        isLoading = true
        errorMessage = nil
        do {
            async let sellerListings = selling.myListings(accessToken: accessToken)
            async let messageThreads = transactions.conversations(accessToken: accessToken)
            async let activeReservations = transactions.reservations(accessToken: accessToken)
            (listings, conversations, reservations) = try await (
                sellerListings, messageThreads, activeReservations
            )
        } catch {
            errorMessage = error.transactionMessage
        }
        isLoading = false
    }
}
