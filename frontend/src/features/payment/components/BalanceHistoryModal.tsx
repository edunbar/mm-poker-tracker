import axios from 'axios';
import { History, Loader2, User, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL } from '../../../config/api';
import { Button } from '../../../shared/ui/button';
import { Heading, Text } from '../../../shared/ui/typography';

interface BalanceHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  playerId: string;
  playerName: string;
  publicCode: string;
}

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

interface Summary {
  poker_net: number;
  payments_sent: number;
  payments_received: number;
  session_count: number;
  payment_count: number;
}

interface HistoryData {
  player: {
    id: string;
    display_name: string;
  };
  amount_owed: number;
  summary: Summary;
  transactions: Transaction[];
  pagination: {
    current_page: number;
    per_page: number;
    total_count: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

const BalanceHistoryModal: React.FC<BalanceHistoryModalProps> = ({
  isOpen,
  onClose,
  playerId,
  playerName,
  publicCode
}) => {
  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<HistoryData | null>(null);
  const [allTransactions, setAllTransactions] = useState<Transaction[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const PER_PAGE = 5;

  const fetchHistory = useCallback(async (isInitial = false, pageToFetch: number = currentPage) => {
    try {
      if (isInitial) {
        setInitialLoading(true);
      } else {
        setLoadingMore(true);
      }

      const params = new URLSearchParams({
        page: pageToFetch.toString(),
        per_page: PER_PAGE.toString()
      });

      const response = await axios.get<HistoryData>(
        `${API_BASE_URL}/api/games/${publicCode}/players/${playerId}/balance-history?${params}`
      );

      setData(response.data);

      if (isInitial) {
        // Initial load - set transactions
        setAllTransactions(response.data.transactions);
      } else {
        // Load more - append transactions
        setAllTransactions(prev => [...prev, ...response.data.transactions]);
      }

      setHasMore(response.data.pagination.has_next);
      setError(null);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.error || 'Failed to load balance history');
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setInitialLoading(false);
      setLoadingMore(false);
    }
  }, [playerId, publicCode, currentPage, PER_PAGE]);

  // Fetch on mount (initial load)
  useEffect(() => {
    if (isOpen && !data) {
      setCurrentPage(1);
      fetchHistory(true, 1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, playerId]);

  // Fetch when currentPage changes (load more)
  useEffect(() => {
    if (isOpen && currentPage > 1) {
      fetchHistory(false, currentPage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, isOpen]);

  // Load more handler
  const handleLoadMore = () => {
    setCurrentPage(prev => {
      return prev + 1;
    });
  };

  // Reset state when modal closes
  const handleClose = () => {
    setAllTransactions([]);
    setCurrentPage(1);
    setHasMore(true);
    setData(null);
    onClose();
  };

  const handleTransactionClick = (transaction: Transaction) => {
    // Session rows are clickable for future navigation to session details
    // For now, we just keep the hover state to indicate they're interactive
    if (transaction.type === 'session' && transaction.session_id) {
      // TODO: Navigate to session detail page when that route is implemented
      // navigate(`/games/${publicCode}/sessions/${transaction.session_id}`);
      // onClose();
    }
  };

  const formatAmount = (amount: number): string => {
    const formatted = Math.abs(amount).toFixed(2);
    return amount >= 0 ? `+$${formatted}` : `-$${formatted}`;
  };

  const formatDateTime = (dateString: string): { date: string; time: string } => {
    const date = new Date(dateString);
    const dateFormatted = new Intl.DateTimeFormat('en-US', {
      month: 'short',
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

  const getTypeLabel = (type: string): string => {
    switch (type) {
      case 'session':
        return 'Cash Game';
      case 'payment_sent':
        return 'Payment Sent';
      case 'payment_received':
        return 'Payment Received';
      default:
        return type;
    }
  };

  // Enrich transactions with previous balance and current flag
  const enrichTransactions = (transactions: Transaction[]): EnrichedTransaction[] => {
    return transactions.map((transaction, index) => {
      const previousBalance = transaction.amount_owed - transaction.amount;
      const isCurrent = index === 0; // Only the first transaction in the list is current

      return {
        ...transaction,
        previousBalance,
        isCurrent
      };
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <History className="h-6 w-6 text-primary" />
              <Heading variant="h4">Balance History</Heading>
            </div>
            <Button
              onClick={handleClose}
              variant="ghost"
              size="icon-sm"
            >
              <X className="h-6 w-6" />
            </Button>
          </div>

          {/* Player Info with Net Balance */}
          <div className="flex items-center justify-between p-4 border border-border rounded-lg">
            <div className="flex items-center gap-3">
              <User className="h-5 w-5 text-primary" />
              <Text className="font-medium">{playerName}</Text>
            </div>
            {data && (
              <div className="flex items-center gap-3">
                <Text className="text-sm text-muted-foreground">Net Balance</Text>
                <Text className={`text-2xl font-bold ${data.amount_owed >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {data.amount_owed >= 0 ? '' : '-'}${Math.abs(data.amount_owed).toFixed(2)}
                </Text>
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-140px)]">
          {initialLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="p-6">
              <Text className="text-destructive">{error}</Text>
            </div>
          ) : data ? (
            <div className="p-6 space-y-6">
              {/* Transaction Table */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <Heading variant="h6">Transactions</Heading>
                  <Text className="text-sm text-muted-foreground">
                    Showing {allTransactions.length} of {data.pagination.total_count}
                  </Text>
                </div>

                <div className="border border-border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-muted">
                      <tr>
                        <th className="text-left px-4 py-3 text-sm font-medium">Date & Time</th>
                        <th className="text-left px-4 py-3 text-sm font-medium">Transaction</th>
                        <th className="text-left px-4 py-3 text-sm font-medium">Type</th>
                        <th className="text-right px-4 py-3 text-sm font-medium">Starting Balance</th>
                        <th className="text-right px-4 py-3 text-sm font-medium">Change</th>
                        <th className="text-right px-4 py-3 text-sm font-medium">Net Balance</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {allTransactions.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                            No transactions found
                          </td>
                        </tr>
                      ) : (
                        enrichTransactions(allTransactions).map((transaction, index) => {
                          const { date, time } = formatDateTime(transaction.date);
                          return (
                            <tr
                              key={`${transaction.type}-${index}`}
                              onClick={() => handleTransactionClick(transaction)}
                              className={`${
                                transaction.type === 'session'
                                  ? 'cursor-pointer hover:bg-muted/50'
                                  : 'cursor-default'
                              }`}
                            >
                              {/* Date & Time Column */}
                              <td className="px-4 py-3">
                                <div className="text-sm">{date}</div>
                                <div className="text-xs text-muted-foreground">{time}</div>
                              </td>

                              {/* Transaction Column */}
                              <td className="px-4 py-3">
                                <Text className="text-sm font-medium">{transaction.description}</Text>
                              </td>

                              {/* Type Column */}
                              <td className="px-4 py-3">
                                <span className="inline-block px-3 py-1 text-xs rounded-full bg-muted text-muted-foreground">
                                  {getTypeLabel(transaction.type)}
                                </span>
                              </td>

                              {/* Starting Balance Column */}
                              <td className="px-4 py-3 text-sm text-right text-muted-foreground">
                                ${transaction.previousBalance.toFixed(2)}
                              </td>

                              {/* Change Column */}
                              <td className={`px-4 py-3 text-sm text-right font-semibold ${
                                transaction.type === 'payment_sent' || transaction.type === 'payment_received'
                                  ? 'text-muted-foreground'
                                  : transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'
                              }`}>
                                {transaction.type === 'payment_sent' || transaction.type === 'payment_received'
                                  ? `$${Math.abs(transaction.amount).toFixed(2)}`
                                  : formatAmount(transaction.amount)
                                }
                              </td>

                              {/* Net Balance Column */}
                              <td className="px-4 py-3 text-right">
                                <div className="text-sm font-semibold">
                                  ${transaction.amount_owed.toFixed(2)}
                                </div>
                                {transaction.isCurrent && (
                                  <div className="text-xs text-green-400 mt-1">
                                    Current
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })

                      )}
                    </tbody>
                  </table>
                </div>

                {/* Load More Button */}
                {hasMore && (
                  <div className="flex justify-center mt-4">
                    <Button
                      onClick={handleLoadMore}
                      disabled={loadingMore}
                      variant="outline"
                      size="default"
                    >
                      {loadingMore ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Loading...
                        </>
                      ) : (
                        'Load More Transactions'
                      )}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default BalanceHistoryModal;
