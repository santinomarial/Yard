import Foundation
import Observation

@MainActor
@Observable
final class ProfileViewModel {
    private(set) var listings: [Listing] = []
    private(set) var conversations: [Conversation] = []
    private(set) var isLoading = true
    var errorMessage: String?

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
            (listings, conversations) = try await (sellerListings, messageThreads)
        } catch {
            errorMessage = error.transactionMessage
        }
        isLoading = false
    }
}
