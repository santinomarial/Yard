import ActivityKit
import SwiftUI
import WidgetKit

@main
struct YardPickupActivityBundle: WidgetBundle {
    var body: some Widget {
        YardPickupActivityWidget()
    }
}

struct YardPickupActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: PickupActivityAttributes.self) { context in
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Label(context.attributes.itemTitle, systemImage: "leaf.fill")
                        .font(.headline)
                    Spacer()
                    Text(context.state.status).font(.caption).foregroundStyle(.secondary)
                }
                Text(context.attributes.meetingZone).font(.title3.weight(.semibold))
                Text(context.attributes.proposedFor, style: .time).font(.subheadline)
                HStack {
                    arrival("Buyer", status: context.state.buyerStatus, eta: context.state.buyerETAMinutes)
                    Spacer()
                    arrival("Seller", status: context.state.sellerStatus, eta: context.state.sellerETAMinutes)
                }
                .font(.caption)
            }
            .padding()
            .activityBackgroundTint(Color(red: 0.96, green: 0.95, blue: 0.91))
            .activitySystemActionForegroundColor(Color(red: 0.64, green: 0.08, blue: 0.16))
            .widgetURL(URL(string: "yard://pickup/\(context.attributes.reservationID)"))
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Label("Pickup", systemImage: "leaf.fill")
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text(context.attributes.proposedFor, style: .time)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    VStack(alignment: .leading) {
                        Text(context.attributes.meetingZone).font(.headline)
                        HStack {
                            arrival("Buyer", status: context.state.buyerStatus, eta: context.state.buyerETAMinutes)
                            Spacer()
                            arrival("Seller", status: context.state.sellerStatus, eta: context.state.sellerETAMinutes)
                        }
                    }
                }
            } compactLeading: {
                Image(systemName: "leaf.fill")
            } compactTrailing: {
                Text(context.attributes.proposedFor, style: .timer)
                    .frame(maxWidth: 48)
            } minimal: {
                Image(systemName: "leaf.fill")
            }
            .widgetURL(URL(string: "yard://pickup/\(context.attributes.reservationID)"))
            .keylineTint(Color(red: 0.64, green: 0.08, blue: 0.16))
        }
    }

    @ViewBuilder
    private func arrival(_ party: String, status: String, eta: Int?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(party).foregroundStyle(.secondary)
            Text(eta.map { "\($0) min" } ?? status).fontWeight(.semibold)
        }
        .accessibilityElement(children: .combine)
    }
}
