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
        queryItems: [URLQueryItem] = [],
        accessToken: String? = nil
    ) async throws -> Response {
        try await request(
            "GET", path: path, queryItems: queryItems, accessToken: accessToken
        )
    }

    func request<Response: Decodable & Sendable, Body: Encodable & Sendable>(
        _ method: String,
        path: String,
        queryItems: [URLQueryItem] = [],
        body: Body? = Optional<Body>.none,
        accessToken: String? = nil
    ) async throws -> Response {
        guard var components = URLComponents(
            url: baseURL.appending(path: path), resolvingAgainstBaseURL: false
        ) else {
            throw APIError.invalidURL
        }
        components.queryItems = queryItems.isEmpty ? nil : queryItems
        guard let url = components.url else { throw APIError.invalidURL }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let accessToken {
            request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            request.httpBody = try JSONEncoder.yard.encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch is CancellationError {
            throw CancellationError()
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

        return try decode(data)
    }

    func request<Response: Decodable & Sendable>(
        _ method: String,
        path: String,
        queryItems: [URLQueryItem] = [],
        accessToken: String? = nil
    ) async throws -> Response {
        try await request(
            method,
            path: path,
            queryItems: queryItems,
            body: Optional<EmptyBody>.none,
            accessToken: accessToken
        )
    }

    func upload(_ data: Data, to url: URL, headers: [String: String]) async throws {
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        for (name, value) in headers {
            request.setValue(value, forHTTPHeaderField: name)
        }
        let response: URLResponse
        do {
            (_, response) = try await session.upload(for: request, from: data)
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw APIError.transport
        }
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.rejected(
                statusCode: httpResponse.statusCode,
                code: "upload_failed",
                message: "The photo upload did not finish. Try again."
            )
        }
    }

    func requestVoid<Body: Encodable & Sendable>(
        _ method: String,
        path: String,
        body: Body? = Optional<Body>.none,
        accessToken: String? = nil
    ) async throws {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw APIError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let accessToken {
            request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            request.httpBody = try JSONEncoder.yard.encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch is CancellationError {
            throw CancellationError()
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
    }

    func requestVoid(
        _ method: String,
        path: String,
        accessToken: String? = nil
    ) async throws {
        try await requestVoid(
            method,
            path: path,
            body: Optional<EmptyBody>.none,
            accessToken: accessToken
        )
    }

    func webSocketTask(path: String, accessToken: String) throws -> URLSessionWebSocketTask {
        guard var components = URLComponents(
            url: baseURL.appending(path: path), resolvingAgainstBaseURL: false
        ) else { throw APIError.invalidURL }
        components.scheme = components.scheme == "https" ? "wss" : "ws"
        guard let url = components.url else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        return session.webSocketTask(with: request)
    }

    private func decode<Response: Decodable & Sendable>(_ data: Data) throws -> Response {
        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decoding
        }
    }
}

private struct EmptyBody: Encodable, Sendable {}

extension JSONDecoder {
    static var yard: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .custom { codingPath in
            let rawKey = codingPath.last?.stringValue ?? ""
            return YardJSONKey(stringValue: rawKey.yardPropertyName)
        }
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let value = try container.decode(String.self)
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = formatter.date(from: value) {
                return date
            }
            formatter.formatOptions = [.withInternetDateTime]
            if let date = formatter.date(from: value) {
                return date
            }
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Expected an ISO-8601 timestamp"
            )
        }
        return decoder
    }
}

private struct YardJSONKey: CodingKey {
    let stringValue: String
    let intValue: Int? = nil

    init(stringValue: String) {
        self.stringValue = stringValue
    }

    init?(intValue: Int) {
        return nil
    }
}

private extension String {
    var yardPropertyName: String {
        let words = split(separator: "_")
        guard let first = words.first, words.count > 1 else { return self }
        return words.dropFirst().reduce(String(first)) { name, word in
            let component: String
            switch word.lowercased() {
            case "id": component = "ID"
            case "ids": component = "IDs"
            case "url": component = "URL"
            default:
                component = word.prefix(1).uppercased() + word.dropFirst()
            }
            return name + component
        }
    }
}

extension JSONEncoder {
    static var yard: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }
}
