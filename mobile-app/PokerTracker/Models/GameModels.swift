import Foundation

// MARK: - Game Summary

struct GameSummary: Codable, Identifiable {
    let id: String
    let gameName: String
    let publicCode: String
    let adminCode: String?
    let totalSessions: Int
    let totalPlayers: Int
    let totalHandsPlayed: Int
    let createdAt: Date
    let lastSessionDate: Date?

    enum CodingKeys: String, CodingKey {
        case id = "game_id"
        case gameName = "game_name"
        case publicCode = "public_code"
        case adminCode = "admin_code"
        case totalSessions = "total_sessions"
        case totalPlayers = "total_players"
        case totalHandsPlayed = "total_hands_played"
        case createdAt = "created_at"
        case lastSessionDate = "last_session_date"
    }
}

// MARK: - Player Statistics

struct PlayerStatistic: Codable, Identifiable {
    var id: String { playerId }

    let playerId: String
    let playerName: String
    let handsPlayed: Int
    let vpip: Double
    let pfr: Double
    let aggressionFrequency: Double
    let playStyle: String
    let styleColor: String?
    let styleDescription: String?
    let flopAF: Double
    let turnAF: Double
    let riverAF: Double

    enum CodingKeys: String, CodingKey {
        case playerId = "player_id"
        case playerName = "player_name"
        case handsPlayed = "hands_played"
        case vpip, pfr
        case aggressionFrequency = "aggression_frequency"
        case playStyle = "play_style"
        case styleColor = "style_color"
        case styleDescription = "style_description"
        case flopAF = "flop_af"
        case turnAF = "turn_af"
        case riverAF = "river_af"
    }
}

// MARK: - Player Summary

struct PlayerSummaryResponse: Codable {
    let rows: [PlayerSummary]
    let totals: PlayerTotals
}

struct PlayerSummary: Codable, Identifiable {
    var id: String { playerId }

    let playerId: String
    let playerName: String
    let sessionsPlayed: Int
    let totalBuyIn: Int
    let totalCashOut: Int
    let netProfit: Int
    let averageProfit: Double
    let biggestWin: Int
    let biggestLoss: Int

    enum CodingKeys: String, CodingKey {
        case playerId = "player_id"
        case playerName = "player_name"
        case sessionsPlayed = "sessions_played"
        case totalBuyIn = "total_buy_in"
        case totalCashOut = "total_cash_out"
        case netProfit = "net_profit"
        case averageProfit = "average_profit"
        case biggestWin = "biggest_win"
        case biggestLoss = "biggest_loss"
    }

    var profitFormatted: String {
        let dollars = Double(netProfit) / 100.0
        return String(format: "$%.2f", dollars)
    }
}

struct PlayerTotals: Codable {
    let totalSessions: Int
    let totalBuyIn: Int
    let totalCashOut: Int
    let totalProfit: Int

    enum CodingKeys: String, CodingKey {
        case totalSessions = "total_sessions"
        case totalBuyIn = "total_buy_in"
        case totalCashOut = "total_cash_out"
        case totalProfit = "total_profit"
    }
}

// MARK: - Analytics

struct PlayerAnalytics: Codable {
    let topPlayers: [AnalyticsPlayer]
    let bottomPlayers: [AnalyticsPlayer]

    enum CodingKeys: String, CodingKey {
        case topPlayers = "top_players"
        case bottomPlayers = "bottom_players"
    }
}

struct AnalyticsPlayer: Codable, Identifiable {
    var id: String { playerId }

    let playerId: String
    let playerName: String
    let value: Double
    let rank: Int

    enum CodingKeys: String, CodingKey {
        case playerId = "player_id"
        case playerName = "player_name"
        case value, rank
    }
}

struct SessionExtremes: Codable {
    let biggestPots: [SessionExtreme]
    let longestSessions: [SessionExtreme]

    enum CodingKeys: String, CodingKey {
        case biggestPots = "biggest_pots"
        case longestSessions = "longest_sessions"
    }
}

struct SessionExtreme: Codable, Identifiable {
    let id: String
    let sessionName: String
    let gameNumber: Int?
    let value: Double

    enum CodingKeys: String, CodingKey {
        case id = "session_id"
        case sessionName = "session_name"
        case gameNumber = "game_number"
        case value
    }
}
