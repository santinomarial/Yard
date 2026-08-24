import Network
import Observation

@MainActor
@Observable
final class ConnectivityMonitor {
    private(set) var isConnected = true
    @ObservationIgnored private let monitor: NWPathMonitor
    @ObservationIgnored private let queue = DispatchQueue(label: "com.santinomarial.yard.connectivity")

    init(monitor: NWPathMonitor = NWPathMonitor()) {
        self.monitor = monitor
        monitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in self?.isConnected = path.status == .satisfied }
        }
        monitor.start(queue: queue)
    }

    deinit { monitor.cancel() }
}
