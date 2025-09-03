# 🎮 Poker Analytics Frontend

Modern React + TypeScript application for managing and analyzing poker game data. Features both PokerNow game import and live game entry capabilities with real-time validation and comprehensive analytics.

## 🏗️ Architecture

### Application Structure
```
frontend/
├── src/
│   ├── app/                      # Core application setup
│   │   ├── App.tsx              # Main app component
│   │   ├── routes.tsx           # Route definitions
│   │   ├── layout/              # Layout components
│   │   │   ├── MainLayout.tsx   # Main page layout
│   │   │   └── Sidebar.tsx      # Navigation sidebar
│   │   ├── providers/           # React providers
│   │   │   └── QueryProvider.tsx # React Query setup
│   │   └── errors/              # Error boundaries
│   │       └── AppErrorBoundary.tsx
│   ├── features/                # Feature-based organization
│   │   ├── admin/               # Admin functionality
│   │   │   ├── pages/          # Admin page components
│   │   │   ├── components/     # Admin-specific components
│   │   │   ├── api/            # Admin API functions
│   │   │   └── lib/            # Admin utility functions
│   │   └── game/               # Game-related features
│   │       ├── pages/          # Game page components
│   │       ├── components/     # Game-specific components
│   │       └── api/            # Game API functions
│   ├── shared/                  # Shared components and utilities
│   │   ├── ui/                 # Reusable UI components
│   │   └── lib/                # Utility functions
│   ├── components/             # Global components
│   ├── contexts/               # React contexts
│   ├── entities/               # Type definitions
│   └── pages/                  # Legacy page components
├── public/                     # Static assets
├── package.json               # Dependencies and scripts
├── tailwind.config.js         # Tailwind CSS configuration
└── tsconfig.json              # TypeScript configuration
```

### Key Design Patterns
- **Feature-Based Architecture**: Components organized by business domain
- **Container/Presentation Pattern**: Smart containers and dumb components
- **Custom Hooks Pattern**: Business logic extracted into reusable hooks
- **Context + React Query**: Hybrid state management approach

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ 
- npm or yarn package manager

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Server
```bash
npm start
```

Application runs at [http://localhost:3000](http://localhost:3000)

### 3. Build for Production
```bash
npm run build
```

## 🎯 Features

### Game Management
- **PokerNow Import**: Import sessions directly from PokerNow URLs
- **Live Game Entry**: Manual entry form for home games
- **Balance Validation**: Real-time game balance checking
- **Player Management**: Dynamic player addition/removal

### Analytics & Reporting
- **Game Summaries**: Player performance across sessions
- **Detailed Ledger**: Session-by-session breakdown
- **Player Statistics**: Win rates, profit/loss tracking
- **Data Visualization**: Performance trends and analytics

### Admin Features
- **Player Verification**: Link player names to stable IDs
- **Data Editing**: Modify session data with audit trails
- **Bulk Operations**: Mass player management
- **System Analytics**: Data integrity and validation

## 🌐 Routing Structure

### Public Routes
- `/` - Landing page with game access
- `/:publicCode` - Game summary (shorthand)
- `/summary/:publicCode` - Game summary (explicit)
- `/ledger/:publicCode` - Game ledger view

### Admin Routes (Protected)
- `/ingest/:publicCode` - PokerNow URL import
- `/live/:publicCode` - Live game entry
- `/players/:publicCode` - Player verification
- `/ledger-analysis/:publicCode` - Advanced analytics
- `/audit/:publicCode` - Audit log viewer

### Route Protection
```typescript
// Protected routes require admin authentication
<ProtectedRoute requireAdmin={true}>
  <AdminComponent />
</ProtectedRoute>
```

## 🔧 State Management

### Architecture Overview
- **Server State**: React Query for API data
- **Client State**: React Context for UI state
- **Form State**: Local useState for forms
- **Route State**: React Router for navigation

### React Query Configuration
```typescript
// Configured in src/app/providers/QueryProvider.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});
```

### Admin Session Context
```typescript
// Admin authentication state management
const { hasAdminSession, adminCode, setAdminSession } = useAdminSession();
```

### API Integration Patterns
```typescript
// Custom hooks for server state
const { data, isLoading, error } = useGetGame(gameUrl);
const uploadMutation = useUploadGame();

// Query keys for cache management
const gameQueryKey = ["gameData", gameUrl];
const summaryQueryKey = ["playerSummaries", publicCode];
```

## 🎨 UI Components & Styling

### Design System
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide Icons**: Consistent iconography
- **Radix UI**: Accessible primitive components
- **Custom Components**: Built on Radix primitives

### Key Components
```typescript
// Shared UI Components
import { Button } from '../shared/ui/button';
import { Table } from '../shared/ui/table';

// Feature Components
import LiveGameForm from '../features/admin/components/LiveGameForm';
import GameDataTable from '../features/game/components/GameDataTable';
```

### Responsive Design
- Mobile-first approach with Tailwind breakpoints
- Adaptive layouts for different screen sizes
- Touch-friendly interactive elements

## 📡 API Integration

### Backend Communication
```typescript
// API base configuration
const API_BASE_URL = 'http://localhost:8000/api/games';

// PokerNow import
const importGame = async (url: string) => {
  const response = await axios.get(`${API_BASE_URL}/get_transactions`, {
    params: { url }
  });
  return response.data;
};

// Live game submission
const submitLiveGame = async (data: LiveGameData) => {
  const response = await axios.post(`${API_BASE_URL}/upload_live`, data, {
    headers: { 'X-Admin-Code': adminCode }
  });
  return response.data;
};
```

### Error Handling
```typescript
// Centralized error handling
const formatErrorMessage = (error: any): string => {
  if (error.response?.data?.error) {
    return error.response.data.error;
  }
  return 'An unexpected error occurred';
};
```

### Data Validation
```typescript
// Form validation utilities
const validateLiveGameData = (players: Player[]): string[] => {
  const errors: string[] = [];
  
  players.forEach((player, index) => {
    if (!player.name.trim()) {
      errors.push(`Player ${index + 1}: Name is required`);
    }
    if (player.buyIn < 0) {
      errors.push(`Player ${index + 1}: Buy-in cannot be negative`);
    }
  });
  
  return errors;
};
```

## 🧪 Testing

### Test Structure
```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage
```

### Testing Patterns
```typescript
// Component testing with React Testing Library
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';

describe('LiveGameForm', () => {
  it('validates player input correctly', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <LiveGameForm onSubmit={jest.fn()} />
      </QueryClientProvider>
    );
    
    // Test validation logic
    const submitButton = screen.getByText('Submit Live Game');
    fireEvent.click(submitButton);
    
    expect(screen.getByText('At least 2 players required')).toBeInTheDocument();
  });
});
```

## 🔧 Configuration

### Environment Variables
```bash
# .env.local (not committed to git)
REACT_APP_API_URL=http://localhost:8000/api/games
REACT_APP_PUBLIC_CODE=C4QROK
REACT_APP_ADMIN_CODE=your-admin-code-here
```

### TypeScript Configuration
```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "es6", "es2017", "es2018"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  }
}
```

### Tailwind Configuration
```javascript
// tailwind.config.js
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {...},
        secondary: {...}
      }
    },
  },
  plugins: [],
}
```

## 🚀 Build & Deployment

### Production Build
```bash
# Create optimized production build
npm run build

# Serve production build locally
npx serve -s build
```

### Build Optimization
- **Code Splitting**: Automatic route-based splitting
- **Tree Shaking**: Unused code elimination
- **Asset Optimization**: Image and bundle optimization
- **Caching**: Aggressive caching strategies

### Deployment Options
```bash
# Static hosting (Netlify, Vercel, S3)
npm run build
# Upload build/ directory

# Docker deployment
FROM node:16-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🐛 Debugging & Troubleshooting

### Common Issues

**Build Fails with TypeScript Errors**
```bash
# Check TypeScript version compatibility
npm list typescript

# Update TypeScript
npm install typescript@latest

# Clear cache
rm -rf node_modules package-lock.json
npm install
```

**React Query Cache Issues**
```typescript
// Clear specific query cache
queryClient.invalidateQueries(['gameData', gameUrl]);

// Clear all cache
queryClient.clear();

// Reset to initial state
queryClient.resetQueries();
```

**API Connection Issues**
```typescript
// Check backend connectivity
const healthCheck = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`);
    console.log('Backend connected:', response.status);
  } catch (error) {
    console.error('Backend connection failed:', error);
  }
};
```

**CSS/Styling Issues**
```bash
# Rebuild Tailwind classes
npm run build:css

# Check for conflicting styles
# Use browser dev tools to inspect computed styles
```

### Debug Mode
```typescript
// Enable React Query devtools
import { ReactQueryDevtools } from 'react-query/devtools';

function App() {
  return (
    <>
      {/* Your app */}
      <ReactQueryDevtools initialIsOpen={false} />
    </>
  );
}
```

## 📈 Performance Optimization

### Bundle Analysis
```bash
# Analyze bundle size
npm run build
npx webpack-bundle-analyzer build/static/js/*.js
```

### Optimization Techniques
- **Lazy Loading**: Route-based code splitting
- **Memoization**: React.memo for expensive components
- **Virtual Scrolling**: For large data tables
- **Image Optimization**: WebP format and lazy loading

### Performance Monitoring
```typescript
// Track component render performance
import { Profiler } from 'react';

function onRenderCallback(id, phase, actualDuration) {
  console.log('Component render:', { id, phase, actualDuration });
}

<Profiler id="GameTable" onRender={onRenderCallback}>
  <GameDataTable data={data} />
</Profiler>
```

## 🔒 Security Considerations

### Data Protection
- Admin codes stored in localStorage (consider more secure alternatives)
- Input validation on all forms
- XSS prevention through proper escaping
- CSRF protection via API headers

### Best Practices
```typescript
// Sanitize user input
const sanitizeInput = (input: string): string => {
  return input.trim().replace(/[<>]/g, '');
};

// Validate admin codes
const isValidAdminCode = (code: string): boolean => {
  return code && code.length >= 32;
};
```

## 🤝 Contributing

### Development Workflow
1. Create feature branch from `main`
2. Follow component naming conventions
3. Add tests for new functionality
4. Update type definitions as needed
5. Submit pull request with description

### Code Style Guidelines
- **Components**: PascalCase (e.g., `GameDataTable`)
- **Hooks**: camelCase starting with "use" (e.g., `useGameData`)
- **Files**: Match component names (e.g., `GameDataTable.tsx`)
- **Props**: Descriptive interfaces (e.g., `GameDataTableProps`)

### Adding New Features
```typescript
// 1. Create component interface
interface NewFeatureProps {
  data: SomeType[];
  onAction: (item: SomeType) => void;
}

// 2. Implement component
export function NewFeature({ data, onAction }: NewFeatureProps) {
  // Implementation
}

// 3. Add to appropriate feature directory
// features/admin/components/NewFeature.tsx
// features/game/components/NewFeature.tsx

// 4. Export from index file
// features/admin/index.ts
export { NewFeature } from './components/NewFeature';
```

## 📚 Dependencies

### Core Dependencies
- **react**: ^18.3.1 - Core React library
- **react-router-dom**: ^7.8.2 - Client-side routing
- **react-query**: ^3.34.0 - Server state management
- **axios**: ^1.11.0 - HTTP client
- **tailwindcss**: ^3.4.13 - CSS framework
- **typescript**: ^4.1.2 - Static type checking

### UI Dependencies
- **@radix-ui/react-dialog**: ^1.1.15 - Modal components
- **lucide-react**: ^0.541.0 - Icon library
- **clsx**: ^2.1.1 - Conditional class names

### Development Dependencies
- **@testing-library/react**: Testing utilities
- **@types/react**: TypeScript definitions
- **autoprefixer**: CSS vendor prefixing

## 📖 API Reference

### Custom Hooks
```typescript
// Game data fetching
const { data, isLoading, error } = useGetGame(gameUrl);

// Session upload
const uploadMutation = useUploadGame();
uploadMutation.mutate({ sessionId, gameData });

// Player summaries
const { data: summaries } = usePlayerSummaries(publicCode);
```

### Utility Functions
```typescript
// Data validation
import { validateGameData } from '../lib/validation';

// Number formatting
import { formatCurrency, formatPercentage } from '../lib/formatters';

// Date utilities
import { formatGameDate } from '../lib/dateUtils';
```

---

**For detailed backend integration, see the main project README and backend documentation.**