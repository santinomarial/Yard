import SwiftUI

struct BuyingIntentComposer: View {
    let onSave: (BuyingIntentDraft) async -> Bool
    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    @State private var maximumPrice = ""
    @State private var condition: ListingCondition?
    @State private var pickupZone = ""
    @State private var isSaving = false

    var body: some View {
        NavigationStack {
            Form {
                Section("What are you looking for?") {
                    TextField("Monitor, mini fridge, desk…", text: $query)
                        .accessibilityIdentifier("wantedQueryField")
                    TextField("Maximum price (optional)", text: $maximumPrice)
                        .keyboardType(.decimalPad)
                    Picker("Minimum condition", selection: $condition) {
                        Text("Any condition").tag(Optional<ListingCondition>.none)
                        ForEach(ListingCondition.allCases, id: \.self) {
                            Text($0.displayName).tag(Optional($0))
                        }
                    }
                    TextField("Pickup area (optional)", text: $pickupZone)
                }
                Section {
                    Text("Yard compares this alert with active and newly published listings. You can review every match before taking action.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Wanted alert")
            .navigationBarTitleDisplayMode(.inline)
            .disabled(isSaving)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        isSaving = true
                        Task {
                            if await onSave(draft) { dismiss() }
                            isSaving = false
                        }
                    }
                    .disabled(query.trimmingCharacters(in: .whitespacesAndNewlines).count < 2)
                    .accessibilityIdentifier("saveWantedAlertButton")
                }
            }
        }
    }

    private var draft: BuyingIntentDraft {
        let decimal = Decimal(string: maximumPrice)
        let cents = decimal.map { NSDecimalNumber(decimal: $0 * 100).intValue }
        let zone = pickupZone.trimmingCharacters(in: .whitespacesAndNewlines)
        return BuyingIntentDraft(
            query: query.trimmingCharacters(in: .whitespacesAndNewlines),
            categoryID: nil,
            maximumPriceCents: cents,
            minimumCondition: condition,
            pickupZone: zone.isEmpty ? nil : zone
        )
    }
}
