#!/bin/bash

# Script to set up the Xcode project for Poker Tracker iOS app

echo "🎯 Setting up Poker Tracker iOS Project..."

# Create Assets catalog directory
mkdir -p PokerTracker/Resources/Assets.xcassets/AppIcon.appiconset

# Create Assets.xcassets Contents.json
cat > PokerTracker/Resources/Assets.xcassets/Contents.json << 'EOF'
{
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}
EOF

# Create AppIcon Contents.json
cat > PokerTracker/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json << 'EOF'
{
  "images" : [
    {
      "idiom" : "universal",
      "platform" : "ios",
      "size" : "1024x1024"
    }
  ],
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}
EOF

echo "✅ Project structure created!"
echo ""
echo "📱 Next steps:"
echo "1. Open Xcode"
echo "2. Click 'Create New Project'"
echo "3. Select 'iOS' → 'App'"
echo "4. Fill in the following details:"
echo "   - Product Name: PokerTracker"
echo "   - Team: (Select your Apple Developer team)"
echo "   - Organization Identifier: com.homegame (or your own)"
echo "   - Interface: SwiftUI"
echo "   - Language: Swift"
echo "5. Save the project in: $(pwd)"
echo "6. After creating, DELETE the default files Xcode creates"
echo "7. Add our existing files:"
echo "   - Right-click project → 'Add Files to PokerTracker'"
echo "   - Select all folders (App, Models, Views, etc.)"
echo "   - Make sure 'Copy items if needed' is UNCHECKED"
echo "   - Click 'Add'"
echo ""
echo "Or run: open . to open this folder in Finder, then create the project there."
