import SwiftUI

struct ReportTargetReference: Identifiable {
    let id = UUID()
    let type: ReportTarget
    let targetID: UUID
    let title: String
}

struct ReportSheet: View {
    let target: ReportTargetReference
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.dismiss) private var dismiss
    @State private var reason = ReportReason.other
    @State private var details = ""
    @State private var isSubmitting = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text(target.title).font(.headline)
                } header: { Text("Reporting") }

                Section("Reason") {
                    Picker("Reason", selection: $reason) {
                        ForEach(ReportReason.allCases, id: \.self) {
                            Text($0.displayName).tag($0)
                        }
                    }
                    .pickerStyle(.inline)
                    .labelsHidden()
                }

                Section("Details (optional)") {
                    TextField("Tell moderators what happened", text: $details, axis: .vertical)
                        .lineLimit(3...8)
                }

                if let errorMessage {
                    Section { Text(errorMessage).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Report")
            .navigationBarTitleDisplayMode(.inline)
            .disabled(isSubmitting)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Submit") { Task { await submit() } }
                        .accessibilityIdentifier("submitReportButton")
                }
            }
        }
    }

    private func submit() async {
        guard let token = environment.session.accessToken else { return }
        isSubmitting = true
        do {
            let trimmed = details.trimmingCharacters(in: .whitespacesAndNewlines)
            try await environment.safety.report(
                ReportSubmission(
                    targetType: target.type,
                    targetID: target.targetID,
                    reason: reason,
                    details: trimmed.isEmpty ? nil : trimmed
                ),
                accessToken: token
            )
            dismiss()
        } catch {
            errorMessage = error.transactionMessage
        }
        isSubmitting = false
    }
}
