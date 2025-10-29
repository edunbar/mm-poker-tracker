import axios from 'axios';
import { ArrowRight, Calendar, CreditCard, DollarSign, ExternalLink, Gamepad2, Loader2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { API_BASE_URL } from '../../../config/api';
import { Button } from '../../../shared/ui/button';
import { Heading, Text } from '../../../shared/ui/typography';

interface Transaction {
  date: string;
  type: 'session' | 'payment_sent' | 'payment_received';
  description: string;
  amount: number;
  amount_owed: number;
  session_id: string | null;
  payment_id: string | null;
  payment_method: string | null;
  to_player_name: string | null;
  from_player_name: string | null;
}

interface EnrichedTransaction extends Transaction {
  previousBalance: number;
  isCurrent: boolean;
}

interface SessionPlayer {
  player_id: string;
  display_name: string;
  buy_in_sum: number;
  cash_out_sum: number;
  in_game: number;
  net: number;
}

interface SessionDetail {
  session_id: string;
  external_id: string;
  game_number: number;
  started_at: string | null;
  players: SessionPlayer[];
  totals: {
    buy_ins: number;
    cash_outs: number;
    in_game: number;
    balance: number;
  };
}

interface TransactionDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  transaction: EnrichedTransaction | null;
  publicCode: string;
}

const TransactionDetailsModal: React.FC<TransactionDetailsModalProps> = ({
  isOpen,
  onClose,
  transaction,
  publicCode
}) => {
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null);
  const [loadingSession, setLoadingSession] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  // Fetch session details when modal opens with a session transaction
  useEffect(() => {
    if (isOpen && transaction && transaction.type === 'session' && transaction.session_id) {
      const fetchSessionDetail = async () => {
        try {
          setLoadingSession(true);
          setSessionError(null);
          const response = await axios.get<SessionDetail>(
            `${API_BASE_URL}/api/games/${publicCode}/sessions/${transaction.session_id}/detail`
          );
          setSessionDetail(response.data);
        } catch (err) {
          setSessionError('Failed to load session details');
        } finally {
          setLoadingSession(false);
        }
      };

      fetchSessionDetail();
    } else {
      // Reset session detail when modal closes or switches to a non-session transaction
      setSessionDetail(null);
      setSessionError(null);
    }
  }, [isOpen, transaction, publicCode]);

  if (!isOpen || !transaction) return null;

  const formatDateTime = (dateString: string): { date: string; time: string } => {
    const date = new Date(dateString);
    const dateFormatted = new Intl.DateTimeFormat('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    }).format(date);
    const timeFormatted = new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    }).format(date);
    return { date: dateFormatted, time: timeFormatted };
  };

  const formatAmount = (amount: number): string => {
    return `$${Math.abs(amount).toFixed(2)}`;
  };

  const { date, time } = formatDateTime(transaction.date);
  const isSession = transaction.type === 'session';
  const isPayment = transaction.type === 'payment_sent' || transaction.type === 'payment_received';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className={`bg-background rounded-lg shadow-xl w-full ${isSession ? 'max-w-3xl' : 'max-w-md'}`}>
        {/* Header */}
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isSession ? (
                <Gamepad2 className="h-6 w-6 text-primary" />
              ) : (
                <CreditCard className="h-6 w-6 text-primary" />
              )}
              <Heading variant="h4">
                {isSession ? 'Session Details' : 'Payment Details'}
              </Heading>
            </div>
            <Button onClick={onClose} variant="ghost" size="icon-sm">
              <X className="h-6 w-6" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Date & Time */}
          <div className="flex items-start gap-3">
            <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div>
              <Text className="text-sm font-medium">Date & Time</Text>
              <Text className="text-sm text-muted-foreground">{date}</Text>
              <Text className="text-sm text-muted-foreground">{time}</Text>
            </div>
          </div>

          {/* Session-specific details */}
          {isSession && (
            <>
              {/* Description */}
              <div className="flex items-start gap-3">
                <Gamepad2 className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <Text className="text-sm font-medium">Session</Text>
                  <Text className="text-sm text-muted-foreground">{transaction.description}</Text>
                </div>
              </div>

              {/* PokerNow Link */}
              {sessionDetail &&
                sessionDetail.external_id &&
                sessionDetail.external_id !== 'N/A' &&
                !sessionDetail.external_id.startsWith('live_') && (
                <div className="flex items-start gap-3">
                  <ExternalLink className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <Text className="text-sm font-medium">PokerNow Link</Text>
                    <a
                      href={`https://www.pokernow.club/games/${sessionDetail.external_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline flex items-center gap-1"
                    >
                      View on PokerNow
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
              )}

              {/* Loading State */}
              {loadingSession && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  <Text className="ml-2 text-sm text-muted-foreground">Loading session details...</Text>
                </div>
              )}

              {/* Error State */}
              {sessionError && (
                <div className="p-4 bg-destructive/10 border border-destructive rounded-lg">
                  <Text className="text-sm text-destructive">{sessionError}</Text>
                </div>
              )}

              {/* Player Breakdown Table */}
              {!loadingSession && !sessionError && sessionDetail && (
                <div className="mt-4">
                  <Heading variant="h6" className="mb-3">Player Breakdown</Heading>
                  <div className="border border-border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted">
                        <tr>
                          <th className="text-left px-3 py-2 font-medium">Player</th>
                          <th className="text-right px-3 py-2 font-medium">Buy-In</th>
                          <th className="text-right px-3 py-2 font-medium">Cash-Out</th>
                          <th className="text-right px-3 py-2 font-medium">Net</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {sessionDetail.players.map((player) => {
                          const netAmount = player.net / 100; // Convert from cents
                          const netColor = netAmount >= 0 ? 'text-green-600' : 'text-red-600';
                          return (
                            <tr key={player.player_id}>
                              <td className="px-3 py-2">{player.display_name}</td>
                              <td className="text-right px-3 py-2">${(player.buy_in_sum / 100).toFixed(2)}</td>
                              <td className="text-right px-3 py-2">${(player.cash_out_sum / 100).toFixed(2)}</td>
                              <td className={`text-right px-3 py-2 font-semibold ${netColor}`}>
                                {netAmount >= 0 ? '+' : '-'}${Math.abs(netAmount).toFixed(2)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot className="bg-muted font-semibold">
                        <tr>
                          <td className="px-3 py-2">Totals</td>
                          <td className="text-right px-3 py-2">${(sessionDetail.totals.buy_ins / 100).toFixed(2)}</td>
                          <td className="text-right px-3 py-2">${(sessionDetail.totals.cash_outs / 100).toFixed(2)}</td>
                          <td className={`text-right px-3 py-2 ${sessionDetail.totals.balance === 0 ? 'text-green-600' : 'text-red-600'}`}>
                            ${(sessionDetail.totals.balance / 100).toFixed(2)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                  {sessionDetail.totals.balance !== 0 && (
                    <div className="mt-2 p-2 bg-destructive/10 border border-destructive rounded">
                      <Text className="text-xs text-destructive">
                        ⚠️ Session does not balance (expected $0.00)
                      </Text>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* Payment-specific details */}
          {isPayment && (
            <>
              {/* Payment Participants */}
              <div className="flex items-start gap-3">
                <ArrowRight className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <Text className="text-sm font-medium">Payment Flow</Text>
                  <div className="flex items-center gap-2 mt-1">
                    <Text className="text-sm text-muted-foreground">
                      {transaction.from_player_name || 'Unknown'}
                    </Text>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    <Text className="text-sm text-muted-foreground">
                      {transaction.to_player_name || 'Unknown'}
                    </Text>
                  </div>
                </div>
              </div>

              {/* Amount */}
              <div className="flex items-start gap-3">
                <DollarSign className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <Text className="text-sm font-medium">Amount</Text>
                  <Text className="text-sm text-muted-foreground">
                    {formatAmount(Math.abs(transaction.amount))}
                  </Text>
                </div>
              </div>

              {/* Payment Method */}
              <div className="flex items-start gap-3">
                <CreditCard className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <Text className="text-sm font-medium">Payment Method</Text>
                  <Text className="text-sm text-muted-foreground">
                    {transaction.payment_method || 'N/A'}
                  </Text>
                </div>
              </div>

              {/* New Balance */}
              <div className="flex items-start gap-3">
                <DollarSign className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <Text className="text-sm font-medium">New Balance</Text>
                  <Text className="text-sm text-muted-foreground">
                    {formatAmount(transaction.amount_owed)}
                  </Text>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-border flex justify-end">
          <Button onClick={onClose} variant="default">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};

export default TransactionDetailsModal;
