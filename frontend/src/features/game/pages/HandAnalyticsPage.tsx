import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { Heading, Text } from "../../../shared/ui/typography";
import { useHandAnalytics } from "../api/getHandAnalytics";
import { useAdaptivePokerStatistics } from "../api/getPokerStatistics";
import PlayingStylesReference from "../components/PlayingStylesReference";
import PokerStatisticsTable from "../components/PokerStatisticsTable";

interface HandAnalyticsPageProps {
  publicCode: string;
}

export default function HandAnalyticsPage({ publicCode }: HandAnalyticsPageProps) {
  const { data, isLoading, error } = useHandAnalytics(publicCode);
  const { data: statsData, isLoading: statsLoading } = useAdaptivePokerStatistics(publicCode);
  const [currentHandIndex, setCurrentHandIndex] = useState<Record<string, number>>({});

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <Heading variant="h1">Hand Analytics</Heading>
          <Text variant="body" color="muted" className="mt-2">
            Hand-by-hand analytics for sessions with detailed game logs
          </Text>
          {data && (
            <Text variant="body" color="muted" className="mt-1">
              Hand data available for {data.total_sessions_with_hand_data} of {data.total_sessions_in_game} sessions
            </Text>
          )}
        </div>

        {/* Poker Statistics Section */}
        <div className="mb-8">
          {statsLoading ? (
            <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-6">
              <Text variant="body" color="muted">Loading poker statistics...</Text>
            </div>
          ) : statsData && statsData.players.length > 0 ? (
            <div className="space-y-6">
              <PokerStatisticsTable players={statsData.players} />
              <PlayingStylesReference />
            </div>
          ) : (
            <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-6">
              <Text variant="body" color="muted">
                No poker statistics available. Statistics are calculated from sessions with detailed hand logs.
              </Text>
            </div>
          )}
        </div>

        {isLoading && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            Loading...
          </div>
        )}

        {!!error && (
          <div className="mb-6 p-4 bg-destructive/10 border-l-4 border-destructive rounded">
            <Text variant="body" color="destructive" weight="medium">Error</Text>
            <Text variant="body" color="destructive">
              {String(error instanceof Error ? error.message : "An error occurred while loading hand analytics")}
            </Text>
          </div>
        )}

        {!isLoading && !error && data && data.sessions.length === 0 && (
          <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-12 text-center">
            <Text variant="body" color="muted">No hand data available yet. Upload hand logs to see analytics.</Text>
          </div>
        )}

        {!isLoading && !error && data && data.sessions.length > 0 && (
          <div className="space-y-6">
            {data.sessions.map((session) => (
              <div
                key={session.session_id}
                className="bg-card text-card-foreground rounded-lg border border-border shadow-sm p-6"
              >
                <div className="mb-4">
                  <Heading variant="h3">
                    Session #{session.session_number} - {session.date}
                  </Heading>
                </div>

                <div className="space-y-2">
                  <Text variant="body">
                    {session.total_hands} hands played over {session.duration_hours} hours (~{session.hands_per_hour} hands/hour)
                  </Text>
                  <Text variant="body">
                    {session.active_players} active players
                  </Text>
                </div>

                {session.top_winners.length > 0 && (
                  <div className="mt-6">
                    <Heading variant="h4" className="mb-3">
                      Most Hands Won
                    </Heading>
                    <div className="space-y-2">
                      {session.top_winners.map((winner, index) => (
                        <div key={winner.player_id} className="flex items-center justify-between p-3 bg-muted/50 rounded-md">
                          <div className="flex items-center gap-3">
                            <Text variant="body" weight="medium" className="text-muted-foreground min-w-[24px]">
                              {index + 1}.
                            </Text>
                            <Text variant="body" weight="medium">
                              {winner.player_name}
                            </Text>
                          </div>
                          <div className="flex items-center gap-4">
                            <Text variant="body">
                              {winner.hands_won} hands
                            </Text>
                            <Text variant="body" weight="medium" className="min-w-[60px] text-right">
                              {winner.win_percentage}%
                            </Text>
                            <Text variant="body" className="text-muted-foreground">
                              (Biggest: ${(winner.biggest_pot / 100).toFixed(2)})
                            </Text>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {session.top_10_hands && session.top_10_hands.length > 0 && (() => {
                  const sessionHandIndex = currentHandIndex[session.session_id] ?? 0;
                  const currentHand = session.top_10_hands[sessionHandIndex];
                  const totalHands = session.top_10_hands.length;

                  if (!currentHand) return null;

                  return (
                    <div className="mt-6">
                      <div className="flex items-center justify-between mb-3">
                        <Heading variant="h4">
                          Top 10 Largest Hands
                        </Heading>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setCurrentHandIndex(prev => ({
                              ...prev,
                              [session.session_id]: Math.max(0, sessionHandIndex - 1)
                            }))}
                            disabled={sessionHandIndex === 0}
                            className="p-2 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                          >
                            <ChevronLeft className="w-5 h-5" />
                          </button>
                          <Text variant="body" className="min-w-[80px] text-center">
                            {sessionHandIndex + 1} of {totalHands}
                          </Text>
                          <button
                            onClick={() => setCurrentHandIndex(prev => ({
                              ...prev,
                              [session.session_id]: Math.min(totalHands - 1, sessionHandIndex + 1)
                            }))}
                            disabled={sessionHandIndex === totalHands - 1}
                            className="p-2 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                          >
                            <ChevronRight className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                      <div className="border border-border rounded-md p-4 bg-card">
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <Text variant="body" weight="semibold">
                              Hand #{currentHand.hand_number}
                            </Text>
                          </div>
                          <div className="text-right">
                            <Text variant="body" weight="semibold" className="text-primary">
                              ${(currentHand.pot_size / 100).toFixed(2)}
                            </Text>
                            {currentHand.winner_name && (
                              <Text variant="bodySmall" color="muted">
                                Won by {currentHand.winner_name}
                              </Text>
                            )}
                          </div>
                        </div>
                        <div className="bg-muted/30 rounded p-3 font-mono text-sm">
                          {currentHand.action_log.map((action, idx) => (
                            <div key={idx} className="py-0.5">
                              <Text variant="bodySmall" className="font-mono">
                                {action}
                              </Text>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}