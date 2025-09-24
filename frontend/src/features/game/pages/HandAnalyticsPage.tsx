import { Heading, Text } from "../../../shared/ui/typography";
import { useHandAnalytics } from "../api/getHandAnalytics";

interface HandAnalyticsPageProps {
  publicCode: string;
}

export default function HandAnalyticsPage({ publicCode }: HandAnalyticsPageProps) {
  const { data, isLoading, error } = useHandAnalytics(publicCode);

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
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}