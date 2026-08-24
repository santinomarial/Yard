import SwiftUI

struct IntentMatchesView: View {
    let intent: BuyingIntent
    @Environment(AppEnvironment.self) private var environment
    @State private var matches: [ListingMatch] = []
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if let errorMessage, matches.isEmpty {
                ContentUnavailableView("Matches unavailable", systemImage: "wifi.exclamationmark", description: Text(errorMessage))
            } else if matches.isEmpty {
                ContentUnavailableView("No matches yet", systemImage: "bell", description: Text("Yard will keep watching for \(intent.query)."))
            } else {
                List(matches) { match in
                    NavigationLink(value: match.listing) {
                        VStack(alignment: .leading, spacing: 4) {
                            SavedListingRow(listing: match.listing)
                            Text("\(Int(match.score * 100))% match")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(YardTheme.Colors.crimson)
                        }
                    }
                }
            }
        }
        .navigationTitle(intent.query)
        .task {
            guard let token = environment.session.accessToken else { return }
            do { matches = try await environment.buyer.matches(intentID: intent.id, accessToken: token) }
            catch { errorMessage = error.buyerMessage }
        }
    }
}
