import Foundation
import Observation
import PhotosUI
import SwiftUI

enum SellSubmissionState: Equatable {
    case editing
    case preparingPhotos
    case analyzing
    case publishing
    case published(Listing)
}

@MainActor
@Observable
final class SellViewModel {
    var title = ""
    var itemDescription = ""
    var categoryID: UUID?
    var condition = ListingCondition.good
    var priceText = ""
    var isFree = false
    var pickupZone = "Harvard Square"
    private(set) var categories: [YardCategory] = []
    private(set) var photos: [PreparedListingPhoto] = []
    private(set) var state = SellSubmissionState.editing
    private(set) var progress = 0.0
    private(set) var errorMessage: String?

    let pickupZones = [
        "Adams House area", "Cabot House area", "Currier House area", "Eliot House area",
        "Harvard Square", "Kirkland House area", "Leverett House area", "Quincy House area",
        "SEC", "Smith Campus Center area", "Quad",
    ]

    var canPublish: Bool {
        title.trimmingCharacters(in: .whitespacesAndNewlines).count >= 3
            && itemDescription.trimmingCharacters(in: .whitespacesAndNewlines).count >= 3
            && categoryID != nil
            && !photos.isEmpty
            && (isFree || priceCents != nil)
            && state == .editing
    }

    func loadCategories(using marketplace: any MarketplaceRepository) async {
        guard categories.isEmpty else { return }
        do {
            categories = try await marketplace.categories().filter { $0.slug != "free" }
        } catch {
            errorMessage = error.marketplaceMessage
        }
    }

    func loadPhotos(from items: [PhotosPickerItem]) async {
        state = .preparingPhotos
        errorMessage = nil
        do {
            var prepared: [PreparedListingPhoto] = []
            for item in items.prefix(8) {
                guard let data = try await item.loadTransferable(type: Data.self) else { continue }
                prepared.append(try await ListingImagePreprocessor.prepare(data))
            }
            photos = prepared
        } catch {
            errorMessage = "One of those photos could not be prepared. Choose another image."
        }
        state = .editing
    }

    func appendCameraPhoto(_ data: Data) async {
        guard photos.count < 8 else { return }
        state = .preparingPhotos
        errorMessage = nil
        do {
            photos.append(try await ListingImagePreprocessor.prepare(data))
        } catch {
            errorMessage = "That photo could not be prepared. Take another photo and try again."
        }
        state = .editing
    }

    func analyze(using analyzer: any ItemAnalysisService) async {
        guard !photos.isEmpty else { return }
        state = .analyzing
        errorMessage = nil
        do {
            let suggestion = try await analyzer.analyze(images: photos)
            if title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                title = suggestion.title
            }
            if itemDescription.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                itemDescription = suggestion.description
            }
            if categoryID == nil,
               let slug = suggestion.categorySlug {
                categoryID = categories.first { $0.slug == slug }?.id
            }
        } catch {
            errorMessage = "Yard could not analyze these photos. You can still finish the listing manually."
        }
        state = .editing
    }

    func publish(using repository: any SellingRepository, accessToken: String) async {
        guard let payload else {
            errorMessage = "Review the required listing details before publishing."
            return
        }
        state = .publishing
        progress = 0
        errorMessage = nil
        do {
            let listing = try await repository.publish(
                draft: payload,
                photos: photos,
                accessToken: accessToken
            ) { [weak self] value in
                await MainActor.run { self?.progress = value }
            }
            state = .published(listing)
        } catch {
            errorMessage = error.marketplaceMessage
            state = .editing
        }
    }

    func makeLocalDraft() -> ListingDraftRecord {
        ListingDraftRecord(
            title: title,
            itemDescription: itemDescription,
            categoryID: categoryID,
            condition: condition,
            priceText: priceText,
            isFree: isFree,
            pickupZone: pickupZone,
            photos: photos.enumerated().map {
                DraftPhotoRecord(sortOrder: $0.offset, data: $0.element.data)
            }
        )
    }

    func makeNextItemDraft() -> ListingDraftRecord {
        ListingDraftRecord(
            title: "",
            itemDescription: "",
            categoryID: categoryID,
            condition: condition,
            priceText: "",
            isFree: false,
            pickupZone: pickupZone,
            photos: []
        )
    }

    func update(_ draft: ListingDraftRecord, readyForBatch: Bool) {
        draft.title = title
        draft.itemDescription = itemDescription
        draft.categoryID = categoryID
        draft.conditionRawValue = condition.rawValue
        draft.priceText = priceText
        draft.isFree = isFree
        draft.pickupZone = pickupZone
        draft.updatedAt = .now
        draft.isReadyForBatch = readyForBatch
        draft.photos = photos.enumerated().map {
            DraftPhotoRecord(sortOrder: $0.offset, data: $0.element.data)
        }
    }

    func restore(_ draft: ListingDraftRecord) {
        title = draft.title
        itemDescription = draft.itemDescription
        categoryID = draft.categoryID
        condition = draft.condition
        priceText = draft.priceText
        isFree = draft.isFree
        pickupZone = draft.pickupZone
        photos = draft.photos.sorted { $0.sortOrder < $1.sortOrder }.map {
            PreparedListingPhoto(id: $0.id, data: $0.data)
        }
        errorMessage = nil
        state = .editing
    }

    func reset() {
        title = ""
        itemDescription = ""
        categoryID = nil
        condition = .good
        priceText = ""
        isFree = false
        pickupZone = "Harvard Square"
        photos = []
        progress = 0
        errorMessage = nil
        state = .editing
    }

    private var payload: ListingDraftPayload? {
        guard let categoryID else { return nil }
        let resolvedPrice: Int
        if isFree {
            resolvedPrice = 0
        } else {
            guard let priceCents else { return nil }
            resolvedPrice = priceCents
        }
        return ListingDraftPayload(
            title: title.trimmingCharacters(in: .whitespacesAndNewlines),
            description: itemDescription.trimmingCharacters(in: .whitespacesAndNewlines),
            categoryID: categoryID,
            subcategoryID: nil,
            priceCents: resolvedPrice,
            isFree: isFree,
            condition: condition,
            pickupZone: pickupZone
        )
    }

    private var priceCents: Int? {
        let normalized = priceText.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "$", with: "")
            .replacingOccurrences(of: ",", with: "")
        guard let decimal = Decimal(string: normalized), decimal > 0 else { return nil }
        return NSDecimalNumber(decimal: decimal * 100).intValue
    }
}

private extension Error {
    var marketplaceMessage: String {
        if let apiError = self as? APIError,
           case let .rejected(_, _, message) = apiError {
            return message
        }
        return "Yard could not connect. Check your connection and try again."
    }
}
