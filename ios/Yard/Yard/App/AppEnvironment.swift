import Foundation
import Observation

@MainActor
@Observable
final class AppEnvironment {
    let marketplace: any MarketplaceRepository
    let selling: any SellingRepository
    let buyer: any BuyerRepository
    let transactions: any TransactionRepository
    let safety: any SafetyRepository
    let notifications: any NotificationRepository
    let connectivity: ConnectivityMonitor
    let session: UserSession
    let apiClient: APIClient

    init(
        marketplace: any MarketplaceRepository,
        selling: (any SellingRepository)? = nil,
        buyer: (any BuyerRepository)? = nil,
        transactions: (any TransactionRepository)? = nil,
        safety: (any SafetyRepository)? = nil,
        notifications: (any NotificationRepository)? = nil,
        connectivity: ConnectivityMonitor? = nil,
        session: UserSession? = nil,
        apiClient: APIClient? = nil
    ) {
        self.marketplace = marketplace
        self.selling = selling ?? PreviewSellingRepository()
        self.buyer = buyer ?? PreviewBuyerRepository()
        self.transactions = transactions ?? PreviewTransactionRepository()
        self.safety = safety ?? PreviewSafetyRepository()
        self.notifications = notifications ?? PreviewNotificationRepository()
        self.connectivity = connectivity ?? ConnectivityMonitor()
        let previewClient = apiClient ?? APIClient(baseURL: URL(string: "http://localhost:8000")!)
        self.apiClient = previewClient
        self.session = session ?? UserSession(
            repository: PreviewAuthenticationRepository(),
            tokenStore: MemoryTokenStore(),
            initialPhase: .signedIn(PreviewAuthenticationRepository().user)
        )
    }

    static func live(bundle: Bundle = .main) -> AppEnvironment {
        let configuredURL = bundle.object(forInfoDictionaryKey: "YARD_API_BASE_URL") as? String
        let baseURL = configuredURL.flatMap(URL.init(string:)) ?? URL(string: "http://localhost:8000")!
        let client = APIClient(baseURL: baseURL)
        let authentication = LiveAuthenticationRepository(client: client)
        let session = UserSession(repository: authentication, tokenStore: KeychainTokenStore())
        return AppEnvironment(
            marketplace: LiveMarketplaceRepository(client: client),
            selling: LiveSellingRepository(client: client),
            buyer: LiveBuyerRepository(client: client),
            transactions: LiveTransactionRepository(client: client),
            safety: LiveSafetyRepository(client: client),
            notifications: LiveNotificationRepository(client: client),
            session: session,
            apiClient: client
        )
    }
}
