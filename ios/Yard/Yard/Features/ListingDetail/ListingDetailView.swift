import SwiftData
import SwiftUI

struct ListingDetailView: View {
    let listing: Listing
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.modelContext) private var modelContext
    @State private var isSaved = false
    @State private var isUpdatingSavedState = false
    @State private var actionMessage: String?
    @State private var conversation: Conversation?
    @State private var reservation: Reservation?
    @State private var isPerformingTransaction = false
    @State private var showsWaitlistPrompt = false
    @State private var reservationKey = UUID().uuidString
    @State private var reportTarget: ReportTargetReference?

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

                Button("Message seller") { Task { await openConversation() } }
                    .buttonStyle(YardPrimaryButtonStyle())
                    .disabled(isPerformingTransaction)
                    .accessibilityIdentifier("messageSellerButton")

                Button("Reserve item") { Task { await reserve() } }
                    .buttonStyle(.bordered)
                    .frame(maxWidth: .infinity)
                    .disabled(isPerformingTransaction || listing.status != .active)
                    .accessibilityIdentifier("reserveListingButton")
            }
            .padding(YardTheme.Spacing.medium)
        }
        .background(YardTheme.Colors.background)
        .navigationTitle("Listing")
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(item: $conversation) { conversation in
            ChatView(conversation: conversation, listingTitle: listing.title)
        }
        .sheet(item: $reservation) { reservation in
            ReservationConfirmationView(reservation: reservation, listing: listing)
        }
        .sheet(item: $reportTarget) { target in
            ReportSheet(target: target)
        }
        .confirmationDialog(
            "This item was just reserved",
            isPresented: $showsWaitlistPrompt,
            titleVisibility: .visible
        ) {
            Button("Join waitlist") { Task { await joinWaitlist() } }
            Button("Not now", role: .cancel) {}
        } message: {
            Text("Join the waitlist and Yard can offer it to you if the current reservation expires or is cancelled.")
        }
        .task { await loadSavedState() }
        .alert("Yard", isPresented: Binding(
            get: { actionMessage != nil },
            set: { if !$0 { actionMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(actionMessage ?? "")
        }
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button(isSaved ? "Unsave" : "Save", systemImage: isSaved ? "bookmark.fill" : "bookmark") {
                    Task { await toggleSaved() }
                }
                    .disabled(isUpdatingSavedState)
                    .accessibilityIdentifier("saveListingButton")
                Menu("More", systemImage: "ellipsis") {
                    Button("Report listing", role: .destructive) {
                        reportTarget = ReportTargetReference(
                            type: .listing, targetID: listing.id, title: listing.title
                        )
                    }
                }
            }
        }
    }

    private func loadSavedState() async {
        guard let token = environment.session.accessToken else { return }
        if let saved = try? await environment.buyer.savedListings(accessToken: token) {
            isSaved = saved.contains { $0.id == listing.id }
        }
    }

    private func toggleSaved() async {
        guard let token = environment.session.accessToken else { return }
        let nextValue = !isSaved
        isUpdatingSavedState = true
        isSaved = nextValue
        MarketplaceLocalStore.setFavorite(
            nextValue,
            listing: listing,
            queueForSync: !environment.connectivity.isConnected,
            context: modelContext
        )
        if !environment.connectivity.isConnected {
            actionMessage = "Saved on this device. Yard will sync when you are back online."
            isUpdatingSavedState = false
            return
        }
        do {
            try await environment.buyer.setSaved(
                nextValue, listingID: listing.id, accessToken: token
            )
        } catch {
            if (error as? APIError) == .transport {
                MarketplaceLocalStore.setFavorite(
                    nextValue,
                    listing: listing,
                    queueForSync: true,
                    context: modelContext
                )
                actionMessage = "Saved on this device. Yard will sync when you are back online."
            } else {
                isSaved.toggle()
                MarketplaceLocalStore.setFavorite(
                    isSaved,
                    listing: listing,
                    queueForSync: false,
                    context: modelContext
                )
                actionMessage = error.buyerMessage
            }
        }
        isUpdatingSavedState = false
    }

    private func openConversation() async {
        guard let token = environment.session.accessToken else { return }
        isPerformingTransaction = true
        do {
            conversation = try await environment.transactions.conversation(
                listingID: listing.id, accessToken: token
            )
        } catch {
            actionMessage = error.transactionMessage
        }
        isPerformingTransaction = false
    }

    private func reserve() async {
        guard let token = environment.session.accessToken else { return }
        isPerformingTransaction = true
        do {
            reservation = try await environment.transactions.reserve(
                listingID: listing.id,
                idempotencyKey: reservationKey,
                accessToken: token
            )
        } catch {
            if error.transactionCode == "listing_already_reserved" {
                showsWaitlistPrompt = true
            } else {
                actionMessage = error.transactionMessage
            }
        }
        isPerformingTransaction = false
    }

    private func joinWaitlist() async {
        guard let token = environment.session.accessToken else { return }
        isPerformingTransaction = true
        do {
            _ = try await environment.transactions.joinWaitlist(
                listingID: listing.id, accessToken: token
            )
            actionMessage = "You joined the waitlist. Yard will notify you if this item becomes available."
        } catch {
            actionMessage = error.transactionMessage
        }
        isPerformingTransaction = false
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
