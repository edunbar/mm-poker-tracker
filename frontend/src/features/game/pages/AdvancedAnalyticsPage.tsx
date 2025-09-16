// @ts-nocheck
import { Crown, Target, Diamond, Flame, Skull, Clock, Frown, Users, Trophy, HelpCircle } from 'lucide-react';
import { useState } from 'react';
import { usePlayerAnalytics } from '../api/getPlayerAnalytics';
import { usePlayerSummaries } from '../api/getPlayerSummaries';
import { useSessionExtremes } from '../api/getSessionExtremes';

// Custom Skull Icon Component
const SkullIcon = ({ className }: { className?: string }) => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 512 512"
    className={className}
    fill="currentColor"
  >
    <path d="m312.8 288h-193.6c-4 28.801-26.398 52-55.199 55.199v48.801c28.801 4 52 26.398 55.199 55.199h192.8c4-28.801 26.398-52 55.199-55.199v-48.801c-28-3.1992-51.199-26.398-54.398-55.199zm-96.801 128c-26.398 0-48-21.602-48-48s21.602-48 48-48 48 21.602 48 48-21.602 48-48 48z"/>
    <path d="m492.8 184.8c-16 5.6016-41.602 11.199-48.801 4-3.1992-4-2.3984-12.801 3.1992-24.801 29.602-66.398-6.3984-132-8-135.2l-8.8008-16-5.6016 17.602c-9.6016 29.602-36 54.398-55.199 60-5.6016 1.6016-10.398 1.6016-12.801 0-14.398-11.203-12.797-33.602-12.797-33.602l0.80078-10.398-10.402 1.5977c-47.199 9.6016-66.398 48.801-74.398 70.398-3.1992-8-4-20.801-4-30.398v-11.199l-10.398 3.1992c-0.80078 0-61.602 19.199-61.602 80 0 26.398 7.1992 48 14.398 64h66.398c-3.1992-13.602-4.8008-30.398-0.80078-42.398l5.6016-16 8.8008 14.398s4 6.3984 12 9.6016c3.1992-9.6016 9.6016-25.602 23.199-42.398l9.6016-12 4.8008 14.398c1.6016 4.8008 8 18.398 16 18.398 7.1992 0 27.199-19.199 41.602-36.801l12.801-16 1.6016 20c0 1.6016 3.1992 37.602-8.8008 60-1.6016 3.1992-1.6016 5.6016-0.80078 7.1992 2.3984 6.3984 14.398 12 20 13.602l6.3984 2.3984-0.80078 6.4023s-0.80078 4-3.1992 8.8008c11.199 8.7969 19.199 22.398 19.199 38.398v52.801c56-16.801 72-91.199 72-132.8v-11.199z"/>
    <path d="m384 240h-336c-17.602 0-32 14.398-32 32v192c0 17.602 14.398 32 32 32h336c17.602 0 32-14.398 32-32v-192c0-17.602-14.398-32-32-32zm0 168h-8c-26.398 0-48 21.602-48 48v8h-224v-8c0-26.398-21.602-48-48-48h-8v-80h8c26.398 0 48-21.602 48-48v-8h224v8c0 26.398 21.602 48 48 48h8z"/>
  </svg>
);

interface AdvancedAnalyticsPageProps {
  publicCode: string;
}

interface PlayerSummaryRow {
  player: string;
  rank: number;
  buyIn: number;
  cashOut: number;
  net: number;
  gamesPlayed: number;
}

interface AnalyticsPlayer {
  player: string;
  gamesPlayed: number;
  net: number;
  rank?: number;
  buyIn?: number;
  cashOut?: number;
  longestStreak?: number;
  sessionInfo?: string;
}

interface AnalyticsCategory {
  title: string;
  icon: any;
  iconColor: string;
  iconBg: string;
  description: string;
  getData: () => AnalyticsPlayer[];
  getValue: (player: AnalyticsPlayer) => string;
  getSubtext: (player: AnalyticsPlayer) => string;
}

export default function AdvancedAnalyticsPage({ publicCode }: AdvancedAnalyticsPageProps) {
  const { data, isLoading, error } = usePlayerSummaries(publicCode);
  const { data: analyticsData, isLoading: analyticsLoading } = usePlayerAnalytics(publicCode);
  const { data: sessionExtremesData, isLoading: sessionExtremesLoading } = useSessionExtremes(publicCode);
  const rows: PlayerSummaryRow[] = data?.rows || [];
  const [activeTab, setActiveTab] = useState<'fame' | 'shame'>('fame');

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount / 100);
  };

  const formatCurrencyFromDollars = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  // Wall of Fame Categories
  const fameCategories: Record<string, AnalyticsCategory> = {
    'biggest-winners': {
      title: 'Biggest Winners',
      icon: Crown,
      iconColor: 'text-sophisticated-gold',
      iconBg: 'bg-sophisticated-gold-extralight',
      description: 'Players with the highest net winnings',
      getData: (): AnalyticsPlayer[] => [...rows].sort((a, b) => b.net - a.net).slice(0, 3).filter(p => p.net > 0).map(p => ({
        player: p.player,
        gamesPlayed: p.gamesPlayed,
        net: p.net,
        rank: p.rank,
        buyIn: p.buyIn,
        cashOut: p.cashOut
      })),
      getValue: (player: AnalyticsPlayer) => formatCurrencyFromDollars(player.net),
      getSubtext: (player: AnalyticsPlayer) => `${player.gamesPlayed} games played`
    },
    'most-consistent': {
      title: 'Most Consistent',
      icon: Target,
      iconColor: 'text-blue-600',
      iconBg: 'bg-blue-100',
      description: 'Highest win rate (net positive ÷ games played)',
      getData: (): AnalyticsPlayer[] => [...rows]
        .filter(p => p.gamesPlayed >= 3 && p.net > 0) // At least 3 games and profitable
        .sort((a, b) => (b.net / b.gamesPlayed) - (a.net / a.gamesPlayed))
        .slice(0, 3)
        .map(p => ({
          player: p.player,
          gamesPlayed: p.gamesPlayed,
          net: p.net,
          rank: p.rank,
          buyIn: p.buyIn,
          cashOut: p.cashOut
        })),
      getValue: (player: AnalyticsPlayer) => formatCurrencyFromDollars(player.net / player.gamesPlayed),
      getSubtext: (_player: AnalyticsPlayer) => `per game average`
    },
    'high-roller': {
      title: 'High Roller',
      icon: Diamond,
      iconColor: 'text-green-600',
      iconBg: 'bg-green-100',
      description: 'Highest total buy-ins (most money invested)',
      getData: (): AnalyticsPlayer[] => [...rows].sort((a, b) => b.buyIn - a.buyIn).slice(0, 3).map(p => ({
        player: p.player,
        gamesPlayed: p.gamesPlayed,
        net: p.net,
        rank: p.rank,
        buyIn: p.buyIn,
        cashOut: p.cashOut
      })),
      getValue: (player: AnalyticsPlayer) => formatCurrencyFromDollars(player.buyIn || 0),
      getSubtext: (_player: AnalyticsPlayer) => `total invested`
    },
    'longest-hot-streak': {
      title: 'Longest Hot Streak',
      icon: Flame,
      iconColor: 'text-orange-600',
      iconBg: 'bg-orange-100',
      description: 'Longest consecutive winning streak (session by session)',
      getData: (): AnalyticsPlayer[] => {
        if (!analyticsData?.analytics) return [];
        return Object.values(analyticsData.analytics)
          .filter(p => p.longest_winning_streak > 0)
          .sort((a, b) => b.longest_winning_streak - a.longest_winning_streak)
          .slice(0, 3)
          .map(p => ({
            player: p.player_name,
            gamesPlayed: p.total_games,
            net: p.longest_winning_streak_net,  // Use streak-specific net, not total net
            longestStreak: p.longest_winning_streak
          }));
      },
      getValue: (player: AnalyticsPlayer) => `${player.longestStreak} sessions`,
      getSubtext: (player: AnalyticsPlayer) => `${formatCurrency(player.net)} during streak`
    },
    'best-single-session': {
      title: 'Best Single Session',
      icon: Target,
      iconColor: 'text-purple-600',
      iconBg: 'bg-purple-100',
      description: 'Highest single session win (cash out + left on table - buy in)',
      getData: (): AnalyticsPlayer[] => {
        if (!sessionExtremesData?.best_sessions) return [];
        return sessionExtremesData.best_sessions
          .slice(0, 3)
          .map(session => ({
            player: session.player_name,
            gamesPlayed: session.game_number || 1,
            net: session.net / 100, // Convert from cents to dollars
            sessionInfo: `Game #${session.game_number || 'N/A'}`
          }));
      },
      getValue: (player: AnalyticsPlayer) => formatCurrencyFromDollars(player.net),
      getSubtext: (player: AnalyticsPlayer) => player.sessionInfo || 'single session'
    },
    'highest-win-rate': {
      title: 'Highest Win Rate',
      icon: Trophy,
      iconColor: 'text-indigo-600',
      iconBg: 'bg-indigo-100',
      description: 'Players with the highest session win percentage (minimum 10 games)',
      getData: (): AnalyticsPlayer[] => {
        if (!analyticsData?.analytics) return [];
        return Object.values(analyticsData.analytics)
          .filter(p => p.total_games >= 10)
          .map(p => {
            const winRate = (p.total_wins / p.total_games) * 100;
            return {
              player: p.player_name,
              gamesPlayed: p.total_games,
              net: p.total_wins,
              longestStreak: p.longest_winning_streak,
              winRate: winRate
            };
          })
          .sort((a, b) => b.winRate - a.winRate)
          .slice(0, 3);
      },
      getValue: (player: AnalyticsPlayer) => `${Math.round(player.winRate || 0)}%`,
      getSubtext: (player: AnalyticsPlayer) => `${player.net}/${player.gamesPlayed} sessions won`
    },
    'most-sessions-won': {
      title: 'Most Sessions Won',
      icon: Trophy,
      iconColor: 'text-green-600',
      iconBg: 'bg-green-100',
      description: 'Players who won the most individual sessions',
      getData: (): AnalyticsPlayer[] => {
        if (!analyticsData?.analytics) return [];
        return Object.values(analyticsData.analytics)
          .filter(p => p.total_games > 0 && p.total_wins > 0)
          .map(p => {
            const winRate = (p.total_wins / p.total_games) * 100;
            return {
              player: p.player_name,
              gamesPlayed: p.total_games,
              net: p.total_wins,
              longestStreak: p.longest_winning_streak,
              winRate: winRate
            };
          })
          .sort((a, b) => b.net - a.net)
          .slice(0, 3);
      },
      getValue: (player: AnalyticsPlayer) => `${player.net} sessions`,
      getSubtext: (player: AnalyticsPlayer) => `${Math.round(player.winRate || 0)}% win rate`
    }
  };

  // Wall of Shame Categories
  const shameCategories: Record<string, AnalyticsCategory> = {
    'biggest-losers': {
      title: 'Biggest Losers',
      icon: Skull,
      iconColor: 'text-red-600',
      iconBg: 'bg-red-100',
      description: 'Players with the biggest losses',
      getData: (): AnalyticsPlayer[] => [...rows].sort((a, b) => a.net - b.net).slice(0, 3).filter(p => p.net < 0).map(p => ({
        player: p.player,
        gamesPlayed: p.gamesPlayed,
        net: p.net,
        rank: p.rank,
        buyIn: p.buyIn,
        cashOut: p.cashOut
      })),
      getValue: (player: AnalyticsPlayer) => formatCurrencyFromDollars(player.net),
      getSubtext: (player: AnalyticsPlayer) => `${player.gamesPlayed} games played`
    },
    'longest-cold-streak': {
      title: 'Longest Cold Streak',
      icon: Clock,
      iconColor: 'text-orange-600',
      iconBg: 'bg-orange-100',
      description: 'Longest consecutive losing streak (session by session)',
      getData: (): AnalyticsPlayer[] => {
        if (!analyticsData?.analytics) return [];
        return Object.values(analyticsData.analytics)
          .filter(p => p.longest_losing_streak > 0)
          .sort((a, b) => b.longest_losing_streak - a.longest_losing_streak)
          .slice(0, 3)
          .map(p => ({
            player: p.player_name,
            gamesPlayed: p.total_games,
            net: p.longest_losing_streak_net,  // Use streak-specific net, not total net
            longestStreak: p.longest_losing_streak
          }));
      },
      getValue: (player: AnalyticsPlayer) => `${player.longestStreak} sessions`,
      getSubtext: (player: AnalyticsPlayer) => `${formatCurrency(player.net)} during streak`
    },
    'worst-efficiency': {
      title: 'Worst Efficiency',
      icon: Frown,
      iconColor: 'text-purple-600',
      iconBg: 'bg-purple-100',
      description: 'Worst average loss per game (minimum 2 games)',
      getData: (): AnalyticsPlayer[] => [...rows]
        .filter(p => p.net < 0 && p.gamesPlayed >= 2)
        .sort((a, b) => (a.net / a.gamesPlayed) - (b.net / b.gamesPlayed))
        .slice(0, 3)
        .map(p => ({
          player: p.player,
          gamesPlayed: p.gamesPlayed,
          net: p.net,
          rank: p.rank,
          buyIn: p.buyIn,
          cashOut: p.cashOut
        })),
      getValue: (player: AnalyticsPlayer) => formatCurrencyFromDollars(player.net / player.gamesPlayed),
      getSubtext: (_player: AnalyticsPlayer) => `average loss per game`
    },
    'most-committed-loser': {
      title: 'Most Committed Loser',
      icon: Users,
      iconColor: 'text-gray-600',
      iconBg: 'bg-gray-100',
      description: 'Players who keep coming back despite losses (most games with negative net)',
      getData: (): AnalyticsPlayer[] => [...rows]
        .filter(p => p.net < 0 && p.gamesPlayed >= 3)
        .sort((a, b) => b.gamesPlayed - a.gamesPlayed)
        .slice(0, 3)
        .map(p => ({
          player: p.player,
          gamesPlayed: p.gamesPlayed,
          net: p.net,
          rank: p.rank,
          buyIn: p.buyIn,
          cashOut: p.cashOut
        })),
      getValue: (player: AnalyticsPlayer) => `${player.gamesPlayed} games`,
      getSubtext: (player: AnalyticsPlayer) => `${formatCurrencyFromDollars(player.net)} total loss`
    },
    'biggest-single-loss': {
      title: 'Biggest Single Loss',
      icon: Target,
      iconColor: 'text-red-600',
      iconBg: 'bg-red-100',
      description: 'Worst single session loss (cash out + left on table - buy in)',
      getData: (): AnalyticsPlayer[] => {
        if (!sessionExtremesData?.worst_sessions) return [];
        return sessionExtremesData.worst_sessions
          .slice(0, 3)
          .map(session => ({
            player: session.player_name,
            gamesPlayed: session.game_number || 1,
            net: session.net / 100, // Convert from cents to dollars
            sessionInfo: `Game #${session.game_number || 'N/A'}`
          }));
      },
      getValue: (player: AnalyticsPlayer) => formatCurrencyFromDollars(player.net),
      getSubtext: (player: AnalyticsPlayer) => player.sessionInfo || 'single session'
    },
    'lowest-win-rate': {
      title: 'Lowest Win Rate',
      icon: Clock,
      iconColor: 'text-amber-600',
      iconBg: 'bg-amber-100',
      description: 'Players with the lowest session win percentage (minimum 10 games)',
      getData: (): AnalyticsPlayer[] => {
        if (!analyticsData?.analytics) return [];
        return Object.values(analyticsData.analytics)
          .filter(p => p.total_games >= 10)
          .map(p => {
            const winRate = (p.total_wins / p.total_games) * 100;
            return {
              player: p.player_name,
              gamesPlayed: p.total_games,
              net: p.total_wins,
              longestStreak: p.longest_losing_streak,
              winRate: winRate
            };
          })
          .sort((a, b) => a.winRate - b.winRate)
          .slice(0, 3);
      },
      getValue: (player: AnalyticsPlayer) => `${Math.round(player.winRate || 0)}%`,
      getSubtext: (player: AnalyticsPlayer) => `${player.net}/${player.gamesPlayed} sessions won`
    },
    'most-sessions-lost': {
      title: 'Most Sessions Lost',
      icon: Clock,
      iconColor: 'text-red-600',
      iconBg: 'bg-red-100',
      description: 'Players who lost the most individual sessions',
      getData: (): AnalyticsPlayer[] => {
        if (!analyticsData?.analytics) return [];
        return Object.values(analyticsData.analytics)
          .filter(p => p.total_games > 0 && p.total_losses > 0)
          .map(p => {
            const lossRate = (p.total_losses / p.total_games) * 100;
            return {
              player: p.player_name,
              gamesPlayed: p.total_games,
              net: p.total_losses,
              longestStreak: p.longest_losing_streak,
              lossRate: lossRate
            };
          })
          .sort((a, b) => b.net - a.net)
          .slice(0, 3);
      },
      getValue: (player: AnalyticsPlayer) => `${player.net} sessions`,
      getSubtext: (player: AnalyticsPlayer) => `${Math.round(player.lossRate || 0)}% loss rate`
    }
  };

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-full mx-auto" style={{ paddingLeft: '200px', paddingRight: '200px' }}>
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Advanced Analytics</h1>
          <p className="mt-2 text-muted-foreground">
            Detailed player performance metrics and achievements
          </p>
        </div>

        {(isLoading || analyticsLoading || sessionExtremesLoading) && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            Loading analytics data...
          </div>
        )}

        {error && (
          <div className="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-4 mb-6">
            <p className="font-medium">Error loading data</p>
            <p className="text-sm">{error.message}</p>
          </div>
        )}

        {!isLoading && !analyticsLoading && !sessionExtremesLoading && !error && rows.length > 0 && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm w-full">
            {/* Tab Navigation */}
            <div className="border-b">
              <nav className="flex space-x-8 p-4">
                <button
                  onClick={() => setActiveTab('fame')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'fame'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Crown className="h-4 w-4" />
                    Wall of Fame
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('shame')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'shame'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Skull className="h-4 w-4" />
                    Wall of Shame
                  </div>
                </button>
              </nav>
            </div>

            {/* Tab Content */}
            <div className="p-8">
              {activeTab === 'fame' && (
                <div className="grid grid-cols-2 gap-8">
                  {Object.entries(fameCategories).map(([key, category]) => {
                    const categoryData = category.getData();

                    return (
                      <div key={key} className="p-6 rounded-lg border border-border">
                        <div className="mb-4">
                          <div className="flex items-center justify-center gap-2">
                            <h4 className="text-lg font-semibold text-foreground text-center">{category.title}</h4>
                            <div className="relative group">
                              <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                              <div className="absolute right-0 top-full mt-2 hidden group-hover:block z-50 w-64 p-3 text-sm text-foreground bg-popover border border-border rounded-lg shadow-xl">
                                <div className="absolute -top-1 right-4 w-2 h-2 bg-popover border-l border-t border-border rotate-45" />
                                <strong>{category.title}</strong><br />
                                {category.description}
                              </div>
                            </div>
                          </div>
                        </div>

                        {categoryData.length === 0 ? (
                          <div className="text-center py-8 text-muted-foreground">
                            No data available
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {categoryData.map((player, index) => (
                              <div key={player.player}>
                                <div className="flex items-center justify-between py-2 gap-4">
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <p className={`text-sm font-semibold ${
                                        index === 0
                                          ? 'text-yellow-500 font-bold'
                                          : 'text-foreground'
                                      }`} style={index === 0 ? { filter: 'drop-shadow(0 0 4px rgba(234, 179, 8, 0.2))' } : {}}>
                                        {player.player}
                                      </p>
                                      {index === 0 && (
                                        <Crown className="h-4 w-4 text-yellow-500" style={{ filter: 'drop-shadow(0 0 4px rgba(234, 179, 8, 0.2))' }} />
                                      )}
                                    </div>
                                    <p className="text-xs text-muted-foreground">{category.getSubtext(player)}</p>
                                  </div>
                                  <div className="text-right">
                                    <p className={`text-sm font-bold ${
                                      index === 0 ? 'text-success' : 'text-white'
                                    }`} style={index === 0 ? { filter: 'drop-shadow(0 0 4px rgba(34, 197, 94, 0.2))' } : {}}>
                                      {category.getValue(player)}
                                    </p>
                                  </div>
                                </div>
                                {index < categoryData.length - 1 && (
                                  <hr className="border-border" />
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {activeTab === 'shame' && (
                <div className="grid grid-cols-2 gap-8">
                  {Object.entries(shameCategories).map(([key, category]) => {
                    const categoryData = category.getData();

                    return (
                      <div key={key} className="p-6 rounded-lg border border-border">
                        <div className="mb-4">
                          <div className="flex items-center justify-center gap-2">
                            <h4 className="text-lg font-semibold text-foreground text-center">{category.title}</h4>
                            <div className="relative group">
                              <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                              <div className="absolute right-0 top-full mt-2 hidden group-hover:block z-50 w-64 p-3 text-sm text-foreground bg-popover border border-border rounded-lg shadow-xl">
                                <div className="absolute -top-1 right-4 w-2 h-2 bg-popover border-l border-t border-border rotate-45" />
                                <strong>{category.title}</strong><br />
                                {category.description}
                              </div>
                            </div>
                          </div>
                        </div>

                        {categoryData.length === 0 ? (
                          <div className="text-center py-8 text-muted-foreground">
                            No data available
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {categoryData.map((player, index) => (
                              <div key={player.player}>
                                <div className="flex items-center justify-between py-2 gap-4">
                                  <div>
                                    <div className="flex items-baseline gap-2">
                                      <p className={`text-sm font-semibold ${
                                        index === 0 ? 'text-red-400' : 'text-foreground'
                                      }`}>
                                        {player.player}
                                      </p>
                                      {index === 0 && (
                                        <SkullIcon className="h-4 w-4 text-red-400" />
                                      )}
                                    </div>
                                    <p className="text-xs text-muted-foreground">{category.getSubtext(player)}</p>
                                  </div>
                                  <div className="text-right">
                                    <p className={`text-sm font-bold ${
                                      index === 0 ? 'text-destructive' : 'text-white'
                                    }`}>
                                      {category.getValue(player)}
                                    </p>
                                  </div>
                                </div>
                                {index < categoryData.length - 1 && (
                                  <hr className="border-border" />
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {!isLoading && !analyticsLoading && !sessionExtremesLoading && !error && rows.length === 0 && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            <p className="text-muted-foreground">No game data available for analytics.</p>
          </div>
        )}
      </div>
    </div>
  );
}