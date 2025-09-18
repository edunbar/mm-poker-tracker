import {
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  Star,
  Crown,
  TrendingUp,
  TrendingDown,
  Minus,
  User,
  Shield,
  Award,
  Target,
  Flame,
  DollarSign
} from 'lucide-react';
import React from 'react';
import { cn } from '../../lib/utils';

// GitHub-inspired badge variants
export type BadgeVariant = 
  | 'default' 
  | 'success' 
  | 'warning' 
  | 'error' 
  | 'info'
  | 'primary'
  | 'secondary';

// Badge sizes
export type BadgeSize = 'sm' | 'md' | 'lg';

// Player status types inspired by GitHub labels
export type PlayerStatus = 
  | 'active'
  | 'inactive' 
  | 'winning'
  | 'losing'
  | 'break-even'
  | 'vip'
  | 'new'
  | 'regular'
  | 'high-roller'
  | 'tournament'
  | 'cash-game'
  | 'online'
  | 'offline';

// Achievement types
export type AchievementType =
  | 'big-winner'
  | 'consistent'
  | 'newcomer'
  | 'veteran'
  | 'streak'
  | 'tournament-winner'
  | 'cash-king'
  | 'grinder'
  | 'risk-taker'
  | 'profitable';

interface BaseBadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
  icon?: React.ReactNode;
  style?: React.CSSProperties;
}

// Core Badge component - GitHub inspired design
export function Badge({ 
  children, 
  variant = 'default', 
  size = 'md',
  className, 
  icon,
  style 
}: BaseBadgeProps) {
  const variants = {
    default: 'badge-github bg-neutral-100 text-neutral-800 border-neutral-200',
    primary: 'badge-github bg-primary/10 text-primary border-primary/20',
    secondary: 'badge-github bg-neutral-100 text-neutral-600 border-neutral-200',
    success: 'badge-github badge-success',
    warning: 'badge-github badge-warning', 
    error: 'badge-github badge-error',
    info: 'badge-github badge-info',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  };

  return (
    <span 
      className={cn(
        'inline-flex items-center gap-1 font-medium border rounded-full transition-colors',
        variants[variant],
        sizes[size],
        className
      )}
      style={style}
    >
      {icon}
      {children}
    </span>
  );
}

// Player Status Badge - GitHub label inspired
interface PlayerStatusBadgeProps {
  status: PlayerStatus;
  size?: BadgeSize;
  className?: string;
  showIcon?: boolean;
}

export function PlayerStatusBadge({ 
  status, 
  size = 'md', 
  className,
  showIcon = true 
}: PlayerStatusBadgeProps) {
  const statusConfig = {
    active: {
      variant: 'success' as const,
      icon: CheckCircle,
      label: 'Active',
    },
    inactive: {
      variant: 'secondary' as const,
      icon: XCircle,
      label: 'Inactive',
    },
    winning: {
      variant: 'success' as const,
      icon: TrendingUp,
      label: 'Winning',
    },
    losing: {
      variant: 'error' as const,
      icon: TrendingDown,
      label: 'Losing',
    },
    'break-even': {
      variant: 'secondary' as const,
      icon: Minus,
      label: 'Break Even',
    },
    vip: {
      variant: 'primary' as const,
      icon: Crown,
      label: 'VIP',
    },
    new: {
      variant: 'info' as const,
      icon: Star,
      label: 'New Player',
    },
    regular: {
      variant: 'default' as const,
      icon: User,
      label: 'Regular',
    },
    'high-roller': {
      variant: 'warning' as const,
      icon: DollarSign,
      label: 'High Roller',
    },
    tournament: {
      variant: 'primary' as const,
      icon: Award,
      label: 'Tournament',
    },
    'cash-game': {
      variant: 'default' as const,
      icon: Target,
      label: 'Cash Game',
    },
    online: {
      variant: 'success' as const,
      icon: CheckCircle,
      label: 'Online',
    },
    offline: {
      variant: 'secondary' as const,
      icon: Clock,
      label: 'Offline',
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <Badge
      variant={config.variant}
      size={size}
      {...(className && { className })}
      {...(showIcon && { icon: <Icon className="w-3 h-3" /> })}
    >
      {config.label}
    </Badge>
  );
}

// Achievement Badge - Special accomplishments
interface AchievementBadgeProps {
  achievement: AchievementType;
  size?: BadgeSize;
  className?: string;
  showIcon?: boolean;
}

export function AchievementBadge({ 
  achievement, 
  size = 'md', 
  className,
  showIcon = true 
}: AchievementBadgeProps) {
  const achievementConfig = {
    'big-winner': {
      variant: 'success' as const,
      icon: Crown,
      label: 'Big Winner',
      color: '#2563eb',
    },
    consistent: {
      variant: 'info' as const,
      icon: Target,
      label: 'Consistent',
      color: '#16a34a',
    },
    newcomer: {
      variant: 'primary' as const,
      icon: Star,
      label: 'Newcomer',
      color: '#0ea5e9',
    },
    veteran: {
      variant: 'warning' as const,
      icon: Shield,
      label: 'Veteran',
      color: '#d97706',
    },
    streak: {
      variant: 'success' as const,
      icon: Flame,
      label: 'On Fire',
      color: '#dc2626',
    },
    'tournament-winner': {
      variant: 'primary' as const,
      icon: Award,
      label: 'Tournament Winner',
      color: '#7c3aed',
    },
    'cash-king': {
      variant: 'warning' as const,
      icon: DollarSign,
      label: 'Cash King',
      color: '#ca8a04',
    },
    grinder: {
      variant: 'secondary' as const,
      icon: Clock,
      label: 'Grinder',
      color: '#6b7280',
    },
    'risk-taker': {
      variant: 'error' as const,
      icon: Zap,
      label: 'Risk Taker',
      color: '#dc2626',
    },
    profitable: {
      variant: 'success' as const,
      icon: TrendingUp,
      label: 'Profitable',
      color: '#16a34a',
    },
  };

  const config = achievementConfig[achievement];
  const Icon = config.icon;

  return (
    <Badge
      variant={config.variant}
      size={size}
      className={cn('font-semibold', className)}
      {...(showIcon && { icon: <Icon className="w-3 h-3" /> })}
    >
      {config.label}
    </Badge>
  );
}

// Numeric Badge - For counts, scores, etc.
interface NumericBadgeProps {
  value: number | string;
  label?: string;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
  format?: 'number' | 'currency' | 'percentage';
}

export function NumericBadge({ 
  value, 
  label, 
  variant = 'default',
  size = 'md',
  className,
  format = 'number'
}: NumericBadgeProps) {
  const formatValue = (val: number | string) => {
    if (typeof val === 'string') return val;
    
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(val);
      case 'percentage':
        return `${val.toFixed(1)}%`;
      default:
        return val.toLocaleString();
    }
  };

  return (
    <Badge
      variant={variant}
      size={size}
      {...(className && { className })}
    >
      {label && <span className="text-muted-foreground">{label}:</span>}
      <span className="font-semibold">{formatValue(value)}</span>
    </Badge>
  );
}

// Badge Group - For displaying multiple related badges
interface BadgeGroupProps {
  badges: Array<{
    id: string;
    content: React.ReactNode;
    variant?: BadgeVariant;
  }>;
  className?: string;
  size?: BadgeSize;
  spacing?: 'tight' | 'normal' | 'wide';
}

export function BadgeGroup({ 
  badges, 
  className, 
  size = 'md',
  spacing = 'normal' 
}: BadgeGroupProps) {
  const spacingClasses = {
    tight: 'gap-1',
    normal: 'gap-2', 
    wide: 'gap-3',
  };

  return (
    <div className={cn(
      'flex flex-wrap items-center',
      spacingClasses[spacing],
      className
    )}>
      {badges.map(badge => (
        <Badge
          key={badge.id}
          {...(badge.variant && { variant: badge.variant })}
          size={size}
        >
          {badge.content}
        </Badge>
      ))}
    </div>
  );
}

// Priority Badge - GitHub issue-style priority indicators
interface PriorityBadgeProps {
  priority: 'low' | 'medium' | 'high' | 'critical';
  size?: BadgeSize;
  className?: string;
}

export function PriorityBadge({ priority, size = 'md', className }: PriorityBadgeProps) {
  const priorityConfig = {
    low: {
      variant: 'secondary' as const,
      label: 'Low Priority',
      color: '#22c55e',
    },
    medium: {
      variant: 'info' as const, 
      label: 'Medium Priority',
      color: '#3b82f6',
    },
    high: {
      variant: 'warning' as const,
      label: 'High Priority', 
      color: '#f59e0b',
    },
    critical: {
      variant: 'error' as const,
      label: 'Critical',
      color: '#ef4444',
    },
  };

  const config = priorityConfig[priority];

  return (
    <Badge
      variant={config.variant}
      size={size}
      {...(className && { className })}
    >
      <div
        className="w-2 h-2 rounded-full mr-1"
        style={{ backgroundColor: config.color }}
      />
      {config.label}
    </Badge>
  );
}

// Custom Label Badge - For user-defined labels like GitHub
interface CustomLabelBadgeProps {
  label: string;
  color: string;
  textColor?: string;
  size?: BadgeSize;
  className?: string;
}

export function CustomLabelBadge({ 
  label, 
  color, 
  textColor, 
  size = 'md', 
  className 
}: CustomLabelBadgeProps) {
  const isDark = (hex: string) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return (r * 299 + g * 587 + b * 114) / 1000 < 128;
  };

  const computedTextColor = textColor || (isDark(color) ? '#ffffff' : '#000000');

  return (
    <Badge
      size={size}
      className={cn('border-0', className)}
      style={{
        backgroundColor: color,
        color: computedTextColor,
      }}
    >
      {label}
    </Badge>
  );
}