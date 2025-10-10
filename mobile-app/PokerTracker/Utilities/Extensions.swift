import Foundation
import SwiftUI

// MARK: - Currency Formatting

extension Int {
    /// Converts cents to formatted dollar string
    var toCurrency: String {
        let dollars = Double(self) / 100.0
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: NSNumber(value: dollars)) ?? "$0.00"
    }
}

extension Double {
    /// Formats a percentage value
    var toPercentage: String {
        return String(format: "%.1f%%", self)
    }
}

// MARK: - Date Formatting

extension Date {
    var shortFormat: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .none
        return formatter.string(from: self)
    }

    var mediumFormat: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: self)
    }
}

// MARK: - Color Extensions

extension Color {
    static let pokerGreen = Color(red: 0.133, green: 0.545, blue: 0.133)
    static let pokerRed = Color(red: 0.8, green: 0.133, blue: 0.133)
    static let cardBackground = Color(white: 0.95)

    /// Returns appropriate text color for positive/negative values
    static func profitColor(for amount: Int) -> Color {
        if amount > 0 {
            return .green
        } else if amount < 0 {
            return .red
        } else {
            return .secondary
        }
    }
}
