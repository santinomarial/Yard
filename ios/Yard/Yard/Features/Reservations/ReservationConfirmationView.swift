import SwiftUI

struct ReservationConfirmationView: View {
    let reservation: Reservation
    let listing: Listing
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: YardTheme.Spacing.large) {
                Image(systemName: "checkmark.seal.fill")
                    .font(.system(size: 58))
                    .foregroundStyle(YardTheme.Colors.crimson)
                    .accessibilityHidden(true)
                Text("Reserved for you")
                    .font(.largeTitle.bold())
                Text(listing.title)
                    .font(.title3.weight(.semibold))
                    .multilineTextAlignment(.center)
                VStack(spacing: YardTheme.Spacing.small) {
                    Text("Complete pickup coordination before")
                        .foregroundStyle(.secondary)
                    Text(reservation.expiresAt, format: .dateTime.weekday().hour().minute())
                        .font(.headline)
                    TimelineView(.periodic(from: .now, by: 1)) { context in
                        Text(countdown(at: context.date))
                            .font(.system(.title2, design: .rounded, weight: .bold))
                            .foregroundStyle(.orange)
                            .monospacedDigit()
                            .accessibilityLabel("Reservation time remaining \(countdown(at: context.date))")
                    }
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(YardTheme.Colors.surface)
                .clipShape(RoundedRectangle(cornerRadius: YardTheme.Radius.card))

                Text("Message the seller to agree on a public place and time. Yard never needs your exact dorm room or live location.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Spacer()
                Button("Done") { dismiss() }
                    .buttonStyle(YardPrimaryButtonStyle())
                    .accessibilityIdentifier("reservationDoneButton")
            }
            .padding(YardTheme.Spacing.large)
            .navigationTitle("Reservation")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
    }

    private func countdown(at date: Date) -> String {
        let remaining = max(0, Int(reservation.expiresAt.timeIntervalSince(date)))
        return String(format: "%02d:%02d", remaining / 60, remaining % 60)
    }
}
