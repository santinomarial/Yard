import Foundation
import Observation

@MainActor
@Observable
final class AppEnvironment {
    let marketplace: any MarketplaceRepository
    let session: UserSession
    let apiClient: APIClient

    init(
        marketplace: any MarketplaceRepository,
        session: UserSession? = nil,
        apiClient: APIClient? = nil
    ) {
        self.marketplace = marketplace
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
            session: session,
            apiClient: client
        )
    }
}
