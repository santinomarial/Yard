import MapKit
import SwiftUI

struct PickupCoordinatorView: View {
    let reservation: Reservation
    @Environment(AppEnvironment.self) private var environment
    @State private var model = PickupCoordinatorViewModel()
    @State private var confirmsCancellation = false

    var body: some View {
        Form {
            Section("Reservation") {
                LabeledContent("Status", value: reservation.status.displayName)
                if reservation.status == .active {
                    LabeledContent("Lease ends") {
                        Text(reservation.expiresAt, format: .dateTime.weekday().hour().minute())
                    }
                }
            }

            if let pickup = model.pickup {
                pickupDetails(pickup)
            } else if reservation.status == .active {
                proposalForm
            }

            if let error = model.errorMessage {
                Section { Text(error).foregroundStyle(.red) }
            }
        }
        .navigationTitle("Pickup")
        .navigationBarTitleDisplayMode(.inline)
        .disabled(model.isWorking)
        .task { await load() }
        .confirmationDialog(
            "Cancel this pickup?",
            isPresented: $confirmsCancellation,
            titleVisibility: .visible
        ) {
            Button("Cancel pickup and reservation", role: .destructive) {
                Task { await cancel() }
            }
            Button("Keep pickup", role: .cancel) {}
        } message: {
            Text("The listing will become available to the next eligible buyer.")
        }
        .accessibilityIdentifier("pickupCoordinatorView")
    }

    private var proposalForm: some View {
        Section {
            Picker("Public meeting area", selection: $model.meetingZone) {
                ForEach(model.meetingZones, id: \.self) { Text($0).tag($0) }
            }
            DatePicker(
                "Time", selection: $model.proposedFor,
                in: Date.now.addingTimeInterval(300)...,
                displayedComponents: [.date, .hourAndMinute]
            )
            Button("Propose pickup") { Task { await propose() } }
                .buttonStyle(YardPrimaryButtonStyle())
                .accessibilityIdentifier("proposePickupButton")
        } header: {
            Text("Coordinate pickup")
        } footer: {
            Text("Choose a public area. Yard never shares an exact address or continuous location.")
        }
    }

    @ViewBuilder
    private func pickupDetails(_ pickup: PickupSession) -> some View {
        Section("Meeting") {
            PickupAreaMap(zone: pickup.meetingZone)
                .frame(height: 190)
                .clipShape(RoundedRectangle(cornerRadius: YardTheme.Radius.card))
            LabeledContent("Area", value: pickup.meetingZone)
            LabeledContent("Time") {
                Text(pickup.proposedFor, format: .dateTime.weekday().month().day().hour().minute())
            }
            LabeledContent("Status", value: pickup.status.displayName)
        }

        if pickup.status == .proposed {
            Section {
                if pickup.proposedBy == environment.session.currentUser?.id {
                    Text("Waiting for the other person to accept this time.")
                        .foregroundStyle(.secondary)
                } else {
                    Button("Accept pickup") { Task { await accept() } }
                        .buttonStyle(YardPrimaryButtonStyle())
                        .accessibilityIdentifier("acceptPickupButton")
                }
            }
        }

        if pickup.status == .scheduled {
            Section("Arrival") {
                LabeledContent("Buyer", value: pickup.buyerArrival.displayName)
                LabeledContent("Seller", value: pickup.sellerArrival.displayName)
                Stepper("My ETA: \(model.etaMinutes) minutes", value: $model.etaMinutes, in: 1...120)
                Button("I'm on the way") { Task { await updatePresence(.onTheWay) } }
                Button("I've arrived") { Task { await updatePresence(.arrived) } }
            }

            Section {
                Button("Confirm exchange completed") { Task { await complete() } }
                    .buttonStyle(YardPrimaryButtonStyle())
                    .accessibilityIdentifier("completeExchangeButton")
            } footer: {
                Text("The exchange is marked complete only after both buyer and seller confirm.")
            }
        }

        if pickup.status == .completed {
            Section {
                Label("Exchange completed", systemImage: "checkmark.seal.fill")
                    .foregroundStyle(.green).font(.headline)
            }
        }

        if pickup.status == .proposed || pickup.status == .scheduled {
            Section {
                Button("Cancel pickup", role: .destructive) { confirmsCancellation = true }
            }
        }
    }

    private func token() -> String? { environment.session.accessToken }
    private func load() async {
        guard let token = token() else { return }
        await model.load(
            reservationID: reservation.id, using: environment.transactions, accessToken: token
        )
    }
    private func propose() async {
        guard let token = token() else { return }
        await model.propose(
            reservationID: reservation.id, using: environment.transactions, accessToken: token
        )
    }
    private func accept() async {
        guard let token = token() else { return }
        await model.accept(
            reservationID: reservation.id, using: environment.transactions, accessToken: token
        )
    }
    private func updatePresence(_ status: ArrivalStatus) async {
        guard let token = token() else { return }
        await model.updatePresence(
            status, reservationID: reservation.id,
            using: environment.transactions, accessToken: token
        )
    }
    private func complete() async {
        guard let token = token() else { return }
        await model.complete(
            reservationID: reservation.id, using: environment.transactions, accessToken: token
        )
    }
    private func cancel() async {
        guard let token = token() else { return }
        await model.cancel(
            reservationID: reservation.id, using: environment.transactions, accessToken: token
        )
    }
}

private struct PickupAreaMap: View {
    let zone: String

    var body: some View {
        Map(initialPosition: .region(region)) {
            Marker(zone, coordinate: coordinate)
                .tint(YardTheme.Colors.crimson)
        }
        .mapStyle(.standard(pointsOfInterest: .excludingAll))
        .allowsHitTesting(false)
        .accessibilityLabel("Map showing the approximate public pickup area at \(zone)")
    }

    private var region: MKCoordinateRegion {
        MKCoordinateRegion(
            center: coordinate,
            span: MKCoordinateSpan(latitudeDelta: 0.012, longitudeDelta: 0.012)
        )
    }

    private var coordinate: CLLocationCoordinate2D {
        switch zone {
        case let value where value.contains("SEC"):
            CLLocationCoordinate2D(latitude: 42.3633, longitude: -71.1271)
        case let value where value.contains("Quad"):
            CLLocationCoordinate2D(latitude: 42.3814, longitude: -71.1255)
        case let value where value.contains("Smith"):
            CLLocationCoordinate2D(latitude: 42.3723, longitude: -71.1182)
        case let value where value.contains("Science Center"):
            CLLocationCoordinate2D(latitude: 42.3764, longitude: -71.1169)
        case let value where value.contains("Lamont"):
            CLLocationCoordinate2D(latitude: 42.3725, longitude: -71.1156)
        default:
            CLLocationCoordinate2D(latitude: 42.3736, longitude: -71.1097)
        }
    }
}

private extension PickupStatus {
    var displayName: String {
        switch self {
        case .proposed: "Proposed"
        case .scheduled: "Scheduled"
        case .completed: "Completed"
        case .cancelled: "Cancelled"
        }
    }
}

private extension ArrivalStatus {
    var displayName: String {
        switch self {
        case .planned: "Planned"
        case .onTheWay: "On the way"
        case .arrived: "Arrived"
        }
    }
}
