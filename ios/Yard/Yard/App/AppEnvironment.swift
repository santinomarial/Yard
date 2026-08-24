import Foundation
import Observation

@MainActor
@Observable
final class AppEnvironment {
    let marketplace: any MarketplaceRepository

    init(marketplace: any MarketplaceRepository) {
        self.marketplace = marketplace
    }

    static func live(bundle: Bundle = .main) -> AppEnvironment {
        let configuredURL = bundle.object(forInfoDictionaryKey: "YARD_API_BASE_URL") as? String
        let baseURL = configuredURL.flatMap(URL.init(string:)) ?? URL(string: "http://localhost:8000")!
        let client = APIClient(baseURL: baseURL)
        return AppEnvironment(marketplace: LiveMarketplaceRepository(client: client))
    }
}

