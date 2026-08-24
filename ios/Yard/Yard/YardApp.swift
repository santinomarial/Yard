import SwiftUI
import SwiftData

@main
struct YardApp: App {
    @UIApplicationDelegateAdaptor(YardAppDelegate.self) private var appDelegate
    @State private var environment = AppEnvironment.live()

    var body: some Scene {
        WindowGroup {
            AuthenticationGate()
                .environment(environment)
                .tint(YardTheme.Colors.crimson)
                .modelContainer(for: [
                    ListingDraftRecord.self,
                    DraftPhotoRecord.self,
                    CachedListingRecord.self,
                    CachedCategoryRecord.self,
                    FavoriteRecord.self,
                    PendingFavoriteMutation.self,
                    CachedConversationRecord.self,
                ])
        }
    }
}
