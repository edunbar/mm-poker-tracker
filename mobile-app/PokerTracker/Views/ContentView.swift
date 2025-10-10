import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            GameSummaryView()
                .tabItem {
                    Label("Games", systemImage: "suit.spade.fill")
                }
                .tag(0)

            AnalyticsView()
                .tabItem {
                    Label("Analytics", systemImage: "chart.bar.fill")
                }
                .tag(1)

            PlayersView()
                .tabItem {
                    Label("Players", systemImage: "person.3.fill")
                }
                .tag(2)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(3)
        }
        .accentColor(.blue)
    }
}

// Placeholder views for each tab
struct GameSummaryView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Game Summary")
                    .font(.largeTitle)
                Text("Your poker games will appear here")
                    .foregroundColor(.secondary)
            }
            .navigationTitle("Games")
        }
    }
}

struct AnalyticsView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Analytics")
                    .font(.largeTitle)
                Text("Player statistics and analytics")
                    .foregroundColor(.secondary)
            }
            .navigationTitle("Analytics")
        }
    }
}

struct PlayersView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Players")
                    .font(.largeTitle)
                Text("Player list and details")
                    .foregroundColor(.secondary)
            }
            .navigationTitle("Players")
        }
    }
}

struct SettingsView: View {
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("API Configuration")) {
                    Text("Backend URL: \(APIService.shared.baseURL)")
                        .font(.caption)
                }

                Section(header: Text("About")) {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}

#Preview {
    ContentView()
}
