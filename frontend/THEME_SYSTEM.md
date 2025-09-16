# Enhanced Theme System

A comprehensive light mode design system inspired by industry-leading platforms: Airtable, Stripe, Linear, and GitHub.

## Overview

This theme system provides a cohesive visual language optimized for professional use that combines:
- **Airtable's** clean dashboard layouts and data organization
- **Stripe's** polished payment interfaces and elevated card designs
- **Linear's** minimal aesthetics and smooth interactions
- **GitHub's** labeling system and status indicators

## Architecture

### 1. Core Theme Files

#### `/src/styles/theme.ts`
- Comprehensive design tokens system
- Component-specific styling helpers
- Type-safe theme configuration

#### `/src/index.css`
- CSS custom properties for consistent theming
- Component utility classes
- Optimized light mode design

#### `/tailwind.config.js`
- Extended Tailwind configuration
- Custom color palettes
- Enhanced typography and spacing

### 2. Component Library

#### Dashboard Components (`/src/components/ui/DashboardLayout.tsx`)
- `DashboardLayout` - Main container with max-width and padding
- `DashboardSection` - Sections with titles, descriptions, and actions
- `DashboardStats` - Metric cards with change indicators
- `DashboardTabs` - Tab navigation with counts and icons
- `DashboardCard` - Elevated content containers

**Inspiration**: Airtable's clean, organized interface design

#### Data Table (`/src/components/ui/DataTable.tsx`)
- Sortable columns with visual feedback
- Row selection and bulk actions
- Empty states and loading indicators
- Sticky headers and responsive design
- Pagination with customizable page sizes

**Inspiration**: Airtable's powerful data grid functionality

#### Payment Components (`/src/components/ui/PaymentTable.tsx`)
- `PaymentSummaryCards` - Key metrics with trend indicators
- `PaymentTransactionTable` - Transaction history with status badges
- `PaymentStatusBadge` - Status indicators with icons
- `BalanceCard` - Account balance with payout information

**Inspiration**: Stripe's transaction and balance interfaces

#### Badge System (`/src/components/ui/Badge.tsx`)
- `Badge` - Core badge component with variants
- `PlayerStatusBadge` - Game-specific player states
- `AchievementBadge` - Player accomplishments
- `NumericBadge` - Formatted numbers and currencies
- `CustomLabelBadge` - User-defined labels

**Inspiration**: GitHub's flexible labeling system

#### Button System (`/src/components/ui/Button.tsx`)
- Multiple variants: primary, secondary, outline, ghost, destructive
- Size options: sm, md, lg, xl
- Loading states and icon support
- Button groups and floating action buttons

**Inspiration**: Linear's clean, purposeful button design

## Design Tokens

### Color System

```css
/* Primary colors - GitHub inspired for actions */
--primary: 0 0% 9%;
--primary-foreground: 0 0% 100%;

/* Success states - GitHub inspired greens */
--badge-success-bg: 142 76% 94%;
--badge-success-text: 142 71% 25%;

/* Table system - Airtable inspired */
--table-header-bg: 0 0% 98%;
--table-row-hover: 210 40% 98%;
--table-row-selected: 210 100% 97%;
```

### Typography

```css
/* Inter font family - Linear inspired */
font-family: 'Inter', 'system-ui', 'sans-serif';

/* Consistent sizing scale */
font-size: 14px; /* Base size */
line-height: 20px; /* Base line height */
```

### Shadows

```css
/* Stripe-inspired elevation */
box-shadow: '0 2px 4px 0 rgba(0, 0, 0, 0.1)'; /* stripe */
box-shadow: '0 8px 32px 0 rgba(0, 0, 0, 0.1)'; /* stripe-lg */
```

## Usage Examples

### Dashboard Layout

```tsx
import { 
  DashboardLayout,
  DashboardSection,
  DashboardStats 
} from '../components/ui/DashboardLayout';

function GameDashboard() {
  const stats = [
    { label: 'Total Players', value: 24, change: '+12%', changeType: 'positive' },
    { label: 'Revenue', value: '$1,250', change: '+8%', changeType: 'positive' }
  ];

  return (
    <DashboardLayout>
      <DashboardSection title="Game Overview">
        <DashboardStats stats={stats} />
      </DashboardSection>
    </DashboardLayout>
  );
}
```

### Data Table

```tsx
import { DataTable, Column } from '../components/ui/DataTable';

const columns: Column<Player>[] = [
  { id: 'name', header: 'Name', accessor: 'name', sortable: true },
  { id: 'winnings', header: 'Winnings', accessor: 'winnings', sortable: true }
];

<DataTable 
  data={players}
  columns={columns}
  onSort={handleSort}
  onRowClick={handleRowClick}
/>
```

### Badge System

```tsx
import { PlayerStatusBadge, NumericBadge } from '../components/ui/Badge';

<PlayerStatusBadge status="winning" />
<NumericBadge value={1500} format="currency" variant="success" />
```

### Buttons

```tsx
import { Button } from '../components/ui/Button';

<Button variant="primary" leftIcon={<Plus />}>
  Add Player
</Button>
```

## Theme Customization

### CSS Custom Properties

The theme uses CSS custom properties for consistent styling:

```css
:root {
  --primary: 0 0% 9%;
  --background: 0 0% 100%;
  --border: 0 0% 90%;
  --muted: 0 0% 96%;
  /* ... other light mode properties */
}
```

### Component Styling

Use utility classes for consistent theming:

```tsx
// Airtable-inspired table
<table className="table-airtable">

// Stripe-inspired card
<div className="card-stripe">

// Linear-inspired button
<button className="btn-linear-primary">

// GitHub-inspired badge
<span className="badge-github badge-success">
```

## Platform Inspirations

### Airtable Influence
- **Dashboard Layouts**: Clean, organized sections with proper spacing
- **Data Tables**: Sortable columns, hover states, selection indicators
- **Stats Display**: Metric cards with clear hierarchy

### Stripe Influence  
- **Payment Tables**: Transaction history with status badges
- **Card Design**: Elevated containers with subtle shadows
- **Color Usage**: Professional, trust-inspiring palette

### Linear Influence
- **Typography**: Inter font with consistent sizing scale
- **Buttons**: Clean, purposeful design with smooth transitions
- **Spacing**: Consistent, predictable spacing system

### GitHub Influence
- **Badge System**: Flexible, colorful status indicators
- **Labels**: User-defined colors and categories
- **State Management**: Clear visual feedback for different states

## Best Practices

1. **Consistency**: Always use theme tokens instead of hardcoded values
2. **Accessibility**: Maintain proper contrast ratios and focus states
3. **Responsiveness**: Components adapt to different screen sizes
4. **Performance**: Minimal CSS with efficient selectors
5. **Maintainability**: Clear component APIs and documentation

## Migration Guide

To update existing components:

1. Replace hardcoded colors with CSS custom properties
2. Use new component classes (`card-stripe`, `btn-linear-primary`, etc.)
3. Import and use new UI components
4. Update badge usage to new Badge system
5. Apply consistent spacing using theme tokens

## Future Enhancements

- [ ] Animation system inspired by Linear's micro-interactions
- [ ] Advanced data visualization components (Airtable-style charts)
- [ ] Enhanced form components with Stripe-style validation
- [ ] Mobile-optimized layouts and interactions