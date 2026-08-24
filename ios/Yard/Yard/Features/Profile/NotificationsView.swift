import SwiftUI

struct NotificationsView: View {
    @Environment(AppEnvironment.self) private var environment
    @State private var notifications: [YardNotification] = []
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if notifications.isEmpty, let errorMessage {
                ContentUnavailableView(
                    "Notifications unavailable",
                    systemImage: "wifi.exclamationmark",
                    description: Text(errorMessage)
                )
            } else if notifications.isEmpty {
                ContentUnavailableView(
                    "No notifications yet",
                    systemImage: "bell",
                    description: Text("Matches, reservations, messages, and pickup reminders will appear here.")
                )
            } else {
                List(notifications) { notification in
                    VStack(alignment: .leading, spacing: 5) {
                        Text(notification.title).font(.headline)
                        Text(notification.body).foregroundStyle(.secondary)
                        Text(notification.createdAt, format: .relative(presentation: .named))
                            .font(.caption).foregroundStyle(.tertiary)
                    }
                    .accessibilityElement(children: .combine)
                }
            }
        }
        .navigationTitle("Notifications")
        .task { await load() }
        .refreshable { await load() }
    }

    private func load() async {
        guard let token = environment.session.accessToken else { return }
        do { notifications = try await environment.notifications.notifications(accessToken: token) }
        catch { errorMessage = error.transactionMessage }
    }
}
