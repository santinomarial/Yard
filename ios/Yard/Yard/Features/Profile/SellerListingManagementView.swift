import Foundation
import SwiftUI

struct SellerListingManagementView: View {
    @Environment(AppEnvironment.self) private var environment
    @State private var listing: Listing
    @State private var price = ""
    @State private var isFree: Bool
    @State private var condition: ListingCondition
    @State private var pickupZone: String
    @State private var isWorking = false
    @State private var errorMessage: String?

    let onUpdate: (Listing) -> Void

    init(listing: Listing, onUpdate: @escaping (Listing) -> Void) {
        _listing = State(initialValue: listing)
        _price = State(
            initialValue: listing.isFree
                ? "" : String(format: "%.2f", Double(listing.priceCents) / 100)
        )
        _isFree = State(initialValue: listing.isFree)
        _condition = State(initialValue: listing.condition)
        _pickupZone = State(initialValue: listing.pickupZone)
        self.onUpdate = onUpdate
    }

    var body: some View {
        Form {
            Section {
                LabeledContent("Status", value: listing.status.displayName)
                LabeledContent("Views", value: listing.viewCount.formatted())
                LabeledContent("Saves", value: listing.saveCount.formatted())
            } header: {
                Text(listing.title)
            } footer: {
                Text("Titles, descriptions, categories, and photos are locked after publication so edited content cannot bypass moderation.")
            }

            Section("Safe listing details") {
                Toggle("Free", isOn: $isFree)
                    .onChange(of: isFree) { _, free in
                        if free { price = "" }
                    }
                TextField("Price", text: $price)
                    .keyboardType(.decimalPad)
                    .disabled(isFree)
                Picker("Condition", selection: $condition) {
                    ForEach(ListingCondition.allCases, id: \.self) { option in
                        Text(option.displayName).tag(option)
                    }
                }
                Picker("Pickup zone", selection: $pickupZone) {
                    ForEach(Self.pickupZones, id: \.self) { zone in
                        Text(zone).tag(zone)
                    }
                    if !Self.pickupZones.contains(pickupZone) {
                        Text(pickupZone).tag(pickupZone)
                    }
                }
                Button("Save safe changes") { Task { await save() } }
                    .disabled(!canEdit || isWorking || priceCents == nil)
            }

            Section("Availability") {
                if listing.status == .active {
                    Button("Mark unavailable", role: .destructive) {
                        Task { await archive() }
                    }
                } else if listing.status == .archived {
                    Button("Relist item") { Task { await relist() } }
                } else {
                    Text(availabilityExplanation)
                        .foregroundStyle(.secondary)
                }
            }

            if let errorMessage {
                Section { Text(errorMessage).foregroundStyle(.red) }
            }
        }
        .navigationTitle("Manage listing")
        .navigationBarTitleDisplayMode(.inline)
        .disabled(isWorking)
        .overlay {
            if isWorking { ProgressView().controlSize(.large) }
        }
        .accessibilityIdentifier("sellerListingManagementView")
    }

    private var canEdit: Bool {
        [.draft, .rejected, .active].contains(listing.status)
    }

    private var priceCents: Int? {
        if isFree { return 0 }
        guard let value = Decimal(string: price), value > 0 else { return nil }
        let cents = value * 100
        return NSDecimalNumber(decimal: cents).intValue
    }

    private var availabilityExplanation: String {
        switch listing.status {
        case .reserved: "Finish or cancel the reservation before changing availability."
        case .sold: "Completed sales stay in your history."
        case .pendingModeration: "This listing is still being reviewed."
        case .removed: "A removed listing cannot be restored."
        default: "Publish this draft before managing availability."
        }
    }

    private func save() async {
        guard let token = environment.session.accessToken, let priceCents else { return }
        await perform {
            try await environment.selling.update(
                listingID: listing.id,
                priceCents: priceCents,
                isFree: isFree,
                condition: condition,
                pickupZone: pickupZone,
                accessToken: token
            )
        }
    }

    private func archive() async {
        guard let token = environment.session.accessToken else { return }
        await perform {
            try await environment.selling.archive(listingID: listing.id, accessToken: token)
        }
    }

    private func relist() async {
        guard let token = environment.session.accessToken else { return }
        await perform {
            try await environment.selling.relist(listingID: listing.id, accessToken: token)
        }
    }

    private func perform(_ operation: () async throws -> Listing) async {
        isWorking = true
        errorMessage = nil
        defer { isWorking = false }
        do {
            listing = try await operation()
            onUpdate(listing)
        } catch {
            errorMessage = error.transactionMessage
        }
    }

    private static let pickupZones = [
        "Harvard Yard", "Science Center", "Smith Campus Center",
        "River Houses", "Quad", "Allston",
    ]
}

#Preview {
    NavigationStack {
        SellerListingManagementView(listing: Listing.previewListings[0]) { _ in }
    }
    .environment(AppEnvironment(marketplace: PreviewMarketplaceRepository()))
}
