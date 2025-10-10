# Poker Tracker iOS App

A native iOS application for the MM Poker Tracker built with Swift and SwiftUI.

## Prerequisites

- Xcode 15.0 or later
- iOS 17.0 or later
- Swift 5.9 or later

## Setup

1. Install Xcode from the Mac App Store if you haven't already
2. Open `PokerTracker.xcodeproj` in Xcode
3. Select your development team in the project settings
4. Build and run the app (Cmd + R)

## Project Structure

```
PokerTracker/
├── App/                    # App configuration and entry point
├── Models/                 # Data models
├── Views/                  # SwiftUI views
├── ViewModels/            # View models for MVVM architecture
├── Services/              # API services and networking
├── Utilities/             # Helper utilities and extensions
└── Resources/             # Assets, colors, and other resources
```

## Architecture

This app follows the MVVM (Model-View-ViewModel) architecture pattern:
- **Models**: Define data structures that match your backend API
- **Views**: SwiftUI views for the UI
- **ViewModels**: Handle business logic and data transformation
- **Services**: Manage API calls to your backend

## API Configuration

The app connects to your backend API. Update the base URL in `Services/APIService.swift`:

```swift
let baseURL = "http://localhost:5001" // Development
// let baseURL = "https://your-production-url.com" // Production
```

## Features

- [ ] View game summaries
- [ ] Player statistics and analytics
- [ ] Hand history
- [ ] Payment tracking
- [ ] Advanced analytics (Wall of Fame/Shame)
- [ ] Rule book access

## Development

To add a new feature:
1. Create the model in `Models/`
2. Create the view in `Views/`
3. Create the view model in `ViewModels/`
4. Add API endpoints in `Services/APIService.swift`
