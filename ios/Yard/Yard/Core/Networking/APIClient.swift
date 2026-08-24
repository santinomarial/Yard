import Foundation

enum APIError: Error, Equatable, Sendable {
    case invalidURL
    case transport
    case invalidResponse
    case rejected(statusCode: Int, code: String, message: String)
    case decoding
}

private struct ErrorEnvelope: Decodable {
    struct APIErrorBody: Decodable {
        let code: String
        let message: String
    }

    let error: APIErrorBody
}

actor APIClient {
    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
        self.decoder = JSONDecoder.yard
    }

    func get<Response: Decodable & Sendable>(
        _ path: String,
        queryItems: [URLQueryItem] = []
    ) async throws -> Response {
        guard var components = URLComponents(
            url: baseURL.appending(path: path), resolvingAgainstBaseURL: false
        ) else {
            throw APIError.invalidURL
        }
        components.queryItems = queryItems.isEmpty ? nil : queryItems
        guard let url = components.url else { throw APIError.invalidURL }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(from: url)
        } catch {
            throw APIError.transport
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            if let envelope = try? decoder.decode(ErrorEnvelope.self, from: data) {
                throw APIError.rejected(
                    statusCode: httpResponse.statusCode,
                    code: envelope.error.code,
                    message: envelope.error.message
                )
            }
            throw APIError.rejected(
                statusCode: httpResponse.statusCode,
                code: "request_failed",
                message: "Yard could not complete this request."
            )
        }

        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decoding
        }
    }
}

extension JSONDecoder {
    static var yard: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}

