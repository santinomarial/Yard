import UIKit
import UserNotifications

extension Notification.Name {
    static let yardDeviceTokenUpdated = Notification.Name("yardDeviceTokenUpdated")
    static let yardDeepLinkReceived = Notification.Name("yardDeepLinkReceived")
}

@MainActor
final class YardAppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    static let deviceTokenDefaultsKey = "yard.apns.device-token"

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        return true
    }

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        UserDefaults.standard.set(token, forKey: Self.deviceTokenDefaultsKey)
        NotificationCenter.default.post(name: .yardDeviceTokenUpdated, object: token)
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        guard let value = response.notification.request.content.userInfo["deep_link"] as? String,
              let url = URL(string: value)
        else { return }
        NotificationCenter.default.post(name: .yardDeepLinkReceived, object: url)
    }
}

enum PushRegistration {
    static func requestAuthorization() async {
        let center = UNUserNotificationCenter.current()
        guard (try? await center.requestAuthorization(options: [.alert, .badge, .sound])) == true
        else { return }
        await MainActor.run { UIApplication.shared.registerForRemoteNotifications() }
    }

    static var storedToken: String? {
        UserDefaults.standard.string(forKey: YardAppDelegate.deviceTokenDefaultsKey)
    }
}
