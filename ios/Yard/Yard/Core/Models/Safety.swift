import Foundation

enum ReportTarget: String, Codable, Sendable {
    case listing
    case user
    case message
}

enum ReportReason: String, Codable, CaseIterable, Sendable {
    case prohibitedItem = "prohibited_item"
    case scamFraud = "scam_fraud"
    case harassment
    case inappropriateContent = "inappropriate_content"
    case counterfeitStolen = "counterfeit_stolen"
    case spam
    case other

    var displayName: String {
        switch self {
        case .prohibitedItem: "Prohibited item"
        case .scamFraud: "Scam or fraud"
        case .harassment: "Harassment"
        case .inappropriateContent: "Inappropriate content"
        case .counterfeitStolen: "Counterfeit or stolen goods"
        case .spam: "Spam"
        case .other: "Other"
        }
    }
}

struct ReportSubmission: Encodable, Sendable {
    let targetType: ReportTarget
    let targetID: UUID
    let reason: ReportReason
    let details: String?
}
