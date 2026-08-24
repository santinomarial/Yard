import Foundation
import ImageIO
import UniformTypeIdentifiers
import Vision

struct ListingDraftSuggestion: Equatable, Sendable {
    let title: String
    let description: String
    let categorySlug: String?
    let recognizedText: [String]
}

protocol ItemAnalysisService: Sendable {
    func analyze(images: [PreparedListingPhoto]) async throws -> ListingDraftSuggestion
}

actor VisionItemAnalysisService: ItemAnalysisService {
    func analyze(images: [PreparedListingPhoto]) async throws -> ListingDraftSuggestion {
        var text: [String] = []
        for image in images.prefix(4) {
            text.append(contentsOf: try await Self.recognizeText(in: image.data))
        }
        var seen = Set<String>()
        let uniqueText = text.filter { seen.insert($0).inserted }
        let combined = uniqueText.joined(separator: " ").lowercased()
        let category = Self.suggestCategory(from: combined)
        let firstUsefulLine = uniqueText.first { $0.count >= 3 && $0.count <= 70 }
        let title = firstUsefulLine ?? Self.fallbackTitle(for: category)
        let description = uniqueText.isEmpty
            ? ""
            : "Visible text: " + uniqueText.prefix(5).joined(separator: ", ")
        return ListingDraftSuggestion(
            title: title,
            description: description,
            categorySlug: category,
            recognizedText: uniqueText
        )
    }

    private nonisolated static func recognizeText(in data: Data) async throws -> [String] {
        try await Task.detached(priority: .userInitiated) {
            guard let source = CGImageSourceCreateWithData(data as CFData, nil),
                  let image = CGImageSourceCreateImageAtIndex(source, 0, nil)
            else { throw ItemAnalysisError.invalidImage }
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true
            try VNImageRequestHandler(cgImage: image).perform([request])
            return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
        }.value
    }

    private nonisolated static func suggestCategory(from text: String) -> String? {
        let signals: [(String, [String])] = [
            ("electronics", ["monitor", "laptop", "keyboard", "sony", "dell", "apple"]),
            ("books", ["textbook", "edition", "isbn", "calculus"]),
            ("kitchen", ["cooker", "cookware", "kitchen", "watt"]),
            ("bikes", ["bicycle", "bike", "helmet"]),
            ("furniture", ["desk", "chair", "table", "shelf"]),
            ("dorm", ["fridge", "bedding", "fan", "mirror"]),
            ("clothing", ["size", "cotton", "jacket", "shoe"]),
        ]
        return signals.first { _, words in words.contains { text.contains($0) } }?.0
    }

    private nonisolated static func fallbackTitle(for category: String?) -> String {
        switch category {
        case "electronics": "Electronics item"
        case "books": "Book"
        case "kitchen": "Kitchen item"
        case "bikes": "Bike item"
        case "furniture": "Furniture item"
        case "dorm": "Dorm item"
        case "clothing": "Clothing item"
        default: "Item for sale"
        }
    }
}

enum ItemAnalysisError: Error, Sendable {
    case invalidImage
}

enum ListingImagePreprocessor {
    static func prepare(_ data: Data) async throws -> PreparedListingPhoto {
        let jpegData = try await Task.detached(priority: .userInitiated) {
            guard let source = CGImageSourceCreateWithData(data as CFData, nil),
                  let image = CGImageSourceCreateThumbnailAtIndex(
                    source,
                    0,
                    [
                        kCGImageSourceCreateThumbnailFromImageAlways: true,
                        kCGImageSourceCreateThumbnailWithTransform: true,
                        kCGImageSourceThumbnailMaxPixelSize: 2_048,
                    ] as CFDictionary
                  )
            else { throw ItemAnalysisError.invalidImage }
            let output = NSMutableData()
            guard let destination = CGImageDestinationCreateWithData(
                output, UTType.jpeg.identifier as CFString, 1, nil
            ) else { throw ItemAnalysisError.invalidImage }
            CGImageDestinationAddImage(
                destination,
                image,
                [kCGImageDestinationLossyCompressionQuality: 0.84] as CFDictionary
            )
            guard CGImageDestinationFinalize(destination) else {
                throw ItemAnalysisError.invalidImage
            }
            return output as Data
        }.value
        guard jpegData.count <= 10 * 1_024 * 1_024 else {
            throw ListingImagePreparationError.tooLarge
        }
        return PreparedListingPhoto(data: jpegData)
    }
}

enum ListingImagePreparationError: Error, Sendable {
    case tooLarge
}
