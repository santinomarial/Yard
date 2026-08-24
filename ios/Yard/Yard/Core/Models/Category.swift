import Foundation

struct YardCategory: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let name: String
    let slug: String
    let symbol: String
    let sortOrder: Int
    let children: [YardCategory]
}

