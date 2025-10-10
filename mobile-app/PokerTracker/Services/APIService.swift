import Foundation

class APIService {
    static let shared = APIService()

    // Update this URL to match your backend
    let baseURL = "http://localhost:5001"

    private init() {}

    // MARK: - Generic API Request

    func request<T: Decodable>(
        endpoint: String,
        method: String = "GET",
        body: Data? = nil
    ) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let body = body {
            request.httpBody = body
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(statusCode: httpResponse.statusCode)
        }

        do {
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    // MARK: - Game Endpoints

    func getGameSummary(publicCode: String) async throws -> GameSummary {
        return try await request(endpoint: "/api/games/\(publicCode)/summary")
    }

    func getPlayerStatistics(publicCode: String) async throws -> [PlayerStatistic] {
        return try await request(endpoint: "/api/games/\(publicCode)/statistics/adaptive")
    }

    func getPlayerSummaries(publicCode: String) async throws -> PlayerSummaryResponse {
        return try await request(endpoint: "/api/games/\(publicCode)/players/summaries")
    }

    // MARK: - Analytics Endpoints

    func getPlayerAnalytics(publicCode: String) async throws -> PlayerAnalytics {
        return try await request(endpoint: "/api/games/\(publicCode)/players/analytics")
    }

    func getSessionExtremes(publicCode: String) async throws -> SessionExtremes {
        return try await request(endpoint: "/api/games/\(publicCode)/sessions/extremes")
    }
}

// MARK: - API Errors

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(statusCode: Int)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let statusCode):
            return "HTTP error: \(statusCode)"
        case .decodingError(let error):
            return "Decoding error: \(error.localizedDescription)"
        }
    }
}
