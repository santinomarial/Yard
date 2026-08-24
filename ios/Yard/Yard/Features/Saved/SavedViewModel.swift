import Foundation
import Observation

enum SavedLoadState: Equatable {
    case loading
    case loaded
    case failed(String)
}

@MainActor
@Observable
final class SavedViewModel {
    private(set) var listings: [Listing] = []
    private(set) var intents: [BuyingIntent] = []
    private(set) var state = SavedLoadState.loading

    func load(using repository: any BuyerRepository, accessToken: String) async {
        state = .loading
        do {
            async let saved = repository.savedListings(accessToken: accessToken)
            async let wanted = repository.intents(accessToken: accessToken)
            (listings, intents) = try await (saved, wanted)
            state = .loaded
        } catch {
            state = .failed(error.buyerMessage)
        }
    }

    func remove(_ listing: Listing, using repository: any BuyerRepository, accessToken: String) async {
        let previous = listings
        listings.removeAll { $0.id == listing.id }
        do {
            try await repository.setSaved(false, listingID: listing.id, accessToken: accessToken)
        } catch {
            listings = previous
            state = .failed(error.buyerMessage)
        }
    }

    func createIntent(_ draft: BuyingIntentDraft, using repository: any BuyerRepository, accessToken: String) async -> Bool {
        do {
            let intent = try await repository.createIntent(draft, accessToken: accessToken)
            intents.insert(intent, at: 0)
            return true
        } catch {
            state = .failed(error.buyerMessage)
            return false
        }
    }
}

extension Error {
    var buyerMessage: String {
        if let error = self as? APIError,
           case let .rejected(_, _, message) = error { return message }
        return "Yard could not sync your saved items. Check your connection and try again."
    }
}
