import SwiftUI

struct ListingDetailView: View {
    let listing: Listing

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: YardTheme.Spacing.large) {
                ListingImage(listing: listing)
                    .frame(height: 340)
                    .clipShape(RoundedRectangle(cornerRadius: YardTheme.Radius.card, style: .continuous))

                VStack(alignment: .leading, spacing: YardTheme.Spacing.small) {
                    Text(listing.formattedPrice)
                        .font(.largeTitle.bold())
                        .foregroundStyle(listing.isFree ? YardTheme.Colors.crimson : .primary)
                    Text(listing.title)
                        .font(.title2.weight(.semibold))
                }

                HStack(spacing: YardTheme.Spacing.medium) {
                    detailPill(listing.condition.displayName, symbol: "sparkles")
                    detailPill(listing.categoryName, symbol: "tag")
                }

                Divider()

                VStack(alignment: .leading, spacing: YardTheme.Spacing.small) {
                    Text("About this item")
                        .font(.headline)
                    Text(listing.description)
                        .font(.body)
                        .foregroundStyle(.secondary)
                }

                VStack(alignment: .leading, spacing: YardTheme.Spacing.small) {
                    Text("Pickup area")
                        .font(.headline)
                    Label(listing.pickupZone, systemImage: "mappin.and.ellipse")
                        .foregroundStyle(.secondary)
                    Text("Exact pickup details stay private until you coordinate with the seller.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Button("Message seller") {}
                    .buttonStyle(YardPrimaryButtonStyle())
                    .accessibilityIdentifier("messageSellerButton")

                Button("Reserve item") {}
                    .buttonStyle(.bordered)
                    .frame(maxWidth: .infinity)
                    .disabled(true)
                    .accessibilityHint("Reservations will become available after account verification.")
            }
            .padding(YardTheme.Spacing.medium)
        }
        .background(YardTheme.Colors.background)
        .navigationTitle("Listing")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button("Save", systemImage: "bookmark") {}
                    .accessibilityIdentifier("saveListingButton")
                Menu("More", systemImage: "ellipsis") {
                    Button("Report listing", role: .destructive) {}
                }
            }
        }
    }

    private func detailPill(_ text: String, symbol: String) -> some View {
        Label(text, systemImage: symbol)
            .font(.subheadline.weight(.medium))
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(YardTheme.Colors.surface)
            .clipShape(Capsule())
    }
}

#Preview {
    NavigationStack { ListingDetailView(listing: Listing.previewListings[0]) }
}

