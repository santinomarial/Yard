import SwiftUI

struct ListingCard: View {
    let listing: Listing

    var body: some View {
        VStack(alignment: .leading, spacing: YardTheme.Spacing.small) {
            ListingImage(listing: listing)
                .frame(height: 148)
                .clipShape(RoundedRectangle(cornerRadius: YardTheme.Radius.card, style: .continuous))

            Text(listing.formattedPrice)
                .font(.headline)
                .foregroundStyle(listing.isFree ? YardTheme.Colors.crimson : .primary)

            Text(listing.title)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.primary)
                .lineLimit(2)

            Label(listing.pickupZone, systemImage: "mappin.and.ellipse")
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            "\(listing.title), \(listing.formattedPrice), \(listing.condition.displayName), pickup near \(listing.pickupZone)"
        )
        .accessibilityIdentifier("listingCard_\(listing.id.uuidString)")
    }
}

struct ListingImage: View {
    let listing: Listing

    var body: some View {
        Group {
            if let imageURL = listing.imageURL {
                AsyncImage(url: imageURL) { phase in
                    switch phase {
                    case let .success(image):
                        image.resizable().scaledToFill()
                    default:
                        placeholder
                    }
                }
            } else {
                placeholder
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .clipped()
    }

    private var placeholder: some View {
        ZStack {
            YardTheme.Colors.surface
            Image(systemName: symbol)
                .font(.system(size: 38, weight: .light))
                .foregroundStyle(YardTheme.Colors.slate)
                .accessibilityHidden(true)
        }
    }

    private var symbol: String {
        switch listing.categoryName.lowercased() {
        case "electronics": "desktopcomputer"
        case "furniture": "chair.lounge"
        case "books": "books.vertical"
        case "bikes": "bicycle"
        case "kitchen": "frying.pan"
        case "clothing": "tshirt"
        case "free": "gift"
        default: "shippingbox"
        }
    }
}

