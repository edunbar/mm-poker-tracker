import axios from 'axios';
import { ChevronDown, ChevronUp, DollarSign, Edit, History, Plus, Target, Trash2, Users, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { API_BASE_URL } from '../../../config/api';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useToast } from '../../../contexts/ToastContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';
import { Button } from '../../../shared/ui/button';
import { Heading, Text } from '../../../shared/ui/typography';

interface PlayerPaymentSummary {
  player_id: string;
  player_name: string;
  poker_net_winnings: number;
  total_paid: number;
  total_received: number;
  realized_cash_earnings?: number;  // Calculated field: received - paid
  net_balance?: number;  // Calculated field: (poker_winnings + paid_out) - received
  days_since_last_payment?: number | null;  // Days since their last payment
}

interface SettlementSuggestion {
  payer_id: string;
  payer_name: string;
  recipient_id: string;
  recipient_name: string;
  amount: number;
}

interface PaymentTransaction {
  id: string;
  payer_name: string;
  recipient_name: string;
  amount: number;
  payment_method: string | null;
  payment_date: string;
  status: string;
  notes: string | null;
  reference_id: string | null;
  created_at: string;
}

interface RecordPaymentForm {
  payer_id: string;
  recipient_id: string;
  amount: string;
  payment_method: string;
  notes: string;
  reference_id: string;
}

export default function PaymentLedgerPage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const { title: _title } = useGameTitle(publicCode || '');
  const { adminCode: sessionAdminCode, hasAdminSession } = useAdminSession();
  const { showSuccess, showError } = useToast();
  const [paymentSummary, setPaymentSummary] = useState<PlayerPaymentSummary[]>([]);
  const [settlements, setSettlements] = useState<SettlementSuggestion[]>([]);
  const [paymentHistory, setPaymentHistory] = useState<PaymentTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'summary' | 'settlements' | 'history' | 'record'>('summary');

  // Sorting state
  const [sortField, setSortField] = useState<keyof PlayerPaymentSummary | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Record payment form state
  const [recordForm, setRecordForm] = useState<RecordPaymentForm>({
    payer_id: '',
    recipient_id: '',
    amount: '',
    payment_method: '',
    notes: '',
    reference_id: ''
  });

  const [manualAdminCode, setManualAdminCode] = useState('');
  const [showAdminInput, setShowAdminInput] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);

  // Edit payment state
  const [editingPayment, setEditingPayment] = useState<PaymentTransaction | null>(null);
  const [editForm, setEditForm] = useState<RecordPaymentForm>({
    payer_id: '',
    recipient_id: '',
    amount: '',
    payment_method: '',
    notes: '',
    reference_id: ''
  });

  // Delete confirmation modal state
  const [paymentToDelete, setPaymentToDelete] = useState<PaymentTransaction | null>(null);

  const getAdminCode = () => {
    return hasAdminSession ? sessionAdminCode : manualAdminCode;
  };

  const fetchPaymentSummary = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/payments/summary`);
      setPaymentSummary(response.data.players);
    } catch (error) {
    }
  };


  const fetchSettlements = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/payments/settlements`);
      setSettlements(response.data.settlements);
    } catch (error) {
    }
  };

  const fetchPaymentHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/payments/history`);
      setPaymentHistory(response.data.transactions);
    } catch (error) {
    }
  };


  useEffect(() => {
    if (publicCode) {
      setLoading(true);
      Promise.all([
        fetchPaymentSummary(),
        fetchSettlements(),
        fetchPaymentHistory()
      ]).finally(() => {
        setLoading(false);
      });
    }
  }, [publicCode]);

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();

    const adminCode = getAdminCode();
    if (!adminCode) {
      setShowAdminInput(true);
      return;
    }

    if (!recordForm.payer_id || !recordForm.recipient_id || !recordForm.amount) {
      showError('Validation Error', 'Please fill in all required fields');
      return;
    }

    setSubmitLoading(true);

    try {
      const paymentData = {
        payer_id: recordForm.payer_id,
        recipient_id: recordForm.recipient_id,
        amount: parseFloat(recordForm.amount),
        payment_method: recordForm.payment_method || null,
        notes: recordForm.notes || null,
        reference_id: recordForm.reference_id || null
      };

      await axios.post(`${API_BASE_URL}/api/games/${publicCode}/payments/record`, paymentData, {
        headers: {
          'X-Admin-Code': adminCode,
          'Content-Type': 'application/json'
        }
      });

      // Reset form and refresh data
      setRecordForm({
        payer_id: '',
        recipient_id: '',
        amount: '',
        payment_method: '',
        notes: '',
        reference_id: ''
      });

      // Refresh all data
      await Promise.all([
        fetchPaymentSummary(),
        fetchSettlements(),
        fetchPaymentHistory()
      ]);

      showSuccess('Payment Recorded', 'Payment recorded successfully!');
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Failed to record payment';
      showError('Payment Error', errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleEditPayment = (payment: PaymentTransaction) => {
    // Find the payer and recipient from paymentSummary
    const payer = paymentSummary.find(p => p.player_name === payment.payer_name);
    const recipient = paymentSummary.find(p => p.player_name === payment.recipient_name);

    setEditingPayment(payment);
    setEditForm({
      payer_id: payer?.player_id || '',
      recipient_id: recipient?.player_id || '',
      amount: payment.amount.toString(),
      payment_method: payment.payment_method || '',
      notes: payment.notes || '',
      reference_id: payment.reference_id || ''
    });
  };

  const handleUpdatePayment = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editingPayment) return;

    const adminCode = getAdminCode();
    if (!adminCode) {
      setShowAdminInput(true);
      return;
    }

    if (!editForm.payer_id || !editForm.recipient_id || !editForm.amount) {
      showError('Validation Error', 'Please fill in all required fields');
      return;
    }

    setSubmitLoading(true);

    try {
      const paymentData = {
        payer_id: editForm.payer_id,
        recipient_id: editForm.recipient_id,
        amount: parseFloat(editForm.amount),
        payment_method: editForm.payment_method || null,
        notes: editForm.notes || null,
        reference_id: editForm.reference_id || null,
        payment_date: editingPayment.payment_date
      };

      await axios.put(`${API_BASE_URL}/api/games/${publicCode}/payments/${editingPayment.id}`, paymentData, {
        headers: {
          'X-Admin-Code': adminCode,
          'Content-Type': 'application/json'
        }
      });

      // Reset form and refresh data
      setEditingPayment(null);
      setEditForm({
        payer_id: '',
        recipient_id: '',
        amount: '',
        payment_method: '',
        notes: '',
        reference_id: ''
      });

      // Refresh all data
      await Promise.all([
        fetchPaymentSummary(),
        fetchSettlements(),
        fetchPaymentHistory()
      ]);

      showSuccess('Payment Updated', 'Payment updated successfully!');
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Failed to update payment';
      showError('Update Error', errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleDeletePayment = (payment: PaymentTransaction) => {
    setPaymentToDelete(payment);
  };

  const confirmDeletePayment = async () => {
    if (!paymentToDelete) return;

    const adminCode = getAdminCode();
    if (!adminCode) {
      setShowAdminInput(true);
      return;
    }

    setSubmitLoading(true);

    try {
      await axios.delete(`${API_BASE_URL}/api/games/${publicCode}/payments/${paymentToDelete.id}`, {
        headers: {
          'X-Admin-Code': adminCode
        }
      });

      // Close modal and refresh data
      setPaymentToDelete(null);
      await Promise.all([
        fetchPaymentSummary(),
        fetchSettlements(),
        fetchPaymentHistory()
      ]);

      showSuccess('Payment Deleted', 'Payment deleted successfully!');
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Failed to delete payment';
      showError('Delete Error', errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleMarkSettlementPaid = async (settlement: SettlementSuggestion) => {
    const adminCode = getAdminCode();
    if (!adminCode) {
      setShowAdminInput(true);
      return;
    }

    setSubmitLoading(true);

    try {
      const paymentData = {
        payer_id: settlement.payer_id,
        recipient_id: settlement.recipient_id,
        amount: settlement.amount,
        payment_method: 'Settlement',
        notes: `Optimal settlement: ${settlement.payer_name} → ${settlement.recipient_name}`
      };

      await axios.post(`${API_BASE_URL}/api/games/${publicCode}/payments/record`, paymentData, {
        headers: {
          'X-Admin-Code': adminCode,
          'Content-Type': 'application/json'
        }
      });

      // Remove the paid settlement from current list
      setSettlements(prev => prev.filter(s =>
        !(s.payer_id === settlement.payer_id &&
          s.recipient_id === settlement.recipient_id &&
          s.amount === settlement.amount)
      ));

      // Refresh payment data but keep settlements stable
      await Promise.all([
        fetchPaymentSummary(),
        fetchPaymentHistory()
      ]);

      showSuccess(
        'Settlement Recorded',
        `Payment recorded: ${settlement.payer_name} paid ${settlement.recipient_name} ${formatCurrency(settlement.amount)}`
      );
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Failed to record settlement payment';
      showError('Settlement Error', errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  const formatCurrency = (cents: number) => {
    // Handle negative zero by normalizing very small values to 0
    const normalized = Math.abs(cents) < 0.005 ? 0 : cents;
    return `$${normalized.toFixed(2)}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const handleSort = (field: keyof PlayerPaymentSummary) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedPaymentSummary = [...paymentSummary].sort((a, b) => {
    if (!sortField) return 0;

    let aValue: any, bValue: any;

    // Handle calculated fields
    if (sortField === 'realized_cash_earnings') {
      aValue = a.total_received - a.total_paid;
      bValue = b.total_received - b.total_paid;
    } else if (sortField === 'net_balance') {
      aValue = (a.poker_net_winnings + a.total_paid) - a.total_received;
      bValue = (b.poker_net_winnings + b.total_paid) - b.total_received;
    } else {
      aValue = a[sortField];
      bValue = b[sortField];
    }

    // Handle string vs number comparison
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      aValue = aValue.toLowerCase();
      bValue = bValue.toLowerCase();
    }

    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  const getSortIcon = (field: keyof PlayerPaymentSummary) => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />;
  };

  // Group settlements by payer
  const groupedSettlements = settlements.reduce((acc, settlement) => {
    const payerId = settlement.payer_id;
    if (!acc[payerId]) {
      acc[payerId] = {
        payer_name: settlement.payer_name,
        total_owed: 0,
        payments: []
      };
    }
    const payerGroup = acc[payerId];
    if (payerGroup) {
      payerGroup.total_owed += settlement.amount;
      payerGroup.payments.push(settlement);
    }
    return acc;
  }, {} as Record<string, {
    payer_name: string;
    total_owed: number;
    payments: SettlementSuggestion[];
  }>);

  // Check if user has admin privileges
  const canEdit = hasAdminSession || manualAdminCode;

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
          <Text variant="body" color="muted" className="mt-2">Loading payment ledger...</Text>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <div>
            <Heading variant="h1">Payment Ledger</Heading>
            <Text variant="body" color="muted" className="mt-2">Track payments and settle debts</Text>
            {!canEdit && (
              <div className="mt-3 p-3 bg-muted border border-border rounded-md">
                <Text variant="bodySmall" color="muted">
                  You're viewing in read-only mode. Admin access is required to add, edit, or mark payments.
                </Text>
              </div>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-border mb-6">
          <nav className="-mb-px flex space-x-8">
            <Button
              onClick={() => setActiveTab('summary')}
              variant="ghost"
              className={`py-2 px-1 border-b-2 font-medium text-sm rounded-none ${
                activeTab === 'summary'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <Users className="w-4 h-4 inline mr-1" />
              Balance Summary
            </Button>
            <Button
              onClick={() => setActiveTab('settlements')}
              variant="ghost"
              className={`py-2 px-1 border-b-2 font-medium text-sm rounded-none ${
                activeTab === 'settlements'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <Target className="w-4 h-4 inline mr-1" />
              Optimal Settlement Structure
            </Button>
            <Button
              onClick={() => setActiveTab('history')}
              variant="ghost"
              className={`py-2 px-1 border-b-2 font-medium text-sm rounded-none ${
                activeTab === 'history'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <History className="w-4 h-4 inline mr-1" />
              Payment History
            </Button>
            {/* Only show Record Payment tab for admin users */}
            {canEdit && (
              <Button
                onClick={() => setActiveTab('record')}
                variant="ghost"
                className={`py-2 px-1 border-b-2 font-medium text-sm rounded-none ${
                  activeTab === 'record'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                }`}
              >
                <Plus className="w-4 h-4 inline mr-1" />
                Record Payment
              </Button>
            )}
          </nav>
        </div>

        {/* Balance Summary Tab */}
        {activeTab === 'summary' && (
          <div className="bg-card text-card-foreground shadow rounded-lg border border-border">
            <div className="px-6 py-4 border-b border-border">
              <Heading variant="h2">Player Balance Summary</Heading>
              <Text variant="bodySmall" color="muted">
                Payment data for all players
              </Text>
            </div>
            <div className="overflow-x-auto overflow-y-visible">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-card border-b border-border">
                  <tr>
                    <th className="px-6 py-3 text-left uppercase tracking-wider">
                      <Button
                        variant="ghost"
                        className="flex items-center space-x-1 hover:text-foreground p-0 h-auto"
                        onClick={() => handleSort('player_name')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Player</Text>
                        {getSortIcon('player_name')}
                      </Button>
                    </th>
                    <th className="px-6 py-3 text-center uppercase tracking-wider">
                      <Button
                        variant="ghost"
                        className="flex items-center justify-center space-x-1 hover:text-foreground p-0 h-auto"
                        onClick={() => handleSort('poker_net_winnings')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Poker Winnings</Text>
                        {getSortIcon('poker_net_winnings')}
                      </Button>
                    </th>
                    <th className="px-6 py-3 text-center uppercase tracking-wider">
                      <Button
                        variant="ghost"
                        className="flex items-center justify-center space-x-1 hover:text-foreground p-0 h-auto"
                        onClick={() => handleSort('total_paid')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Paid Out</Text>
                        {getSortIcon('total_paid')}
                      </Button>
                    </th>
                    <th className="px-6 py-3 text-center uppercase tracking-wider">
                      <Button
                        variant="ghost"
                        className="flex items-center justify-center space-x-1 hover:text-foreground p-0 h-auto"
                        onClick={() => handleSort('total_received')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Received</Text>
                        {getSortIcon('total_received')}
                      </Button>
                    </th>
                    <th className="px-6 py-3 text-center uppercase tracking-wider">
                      <Button
                        variant="ghost"
                        className="flex items-center justify-center space-x-1 hover:text-foreground p-0 h-auto"
                        onClick={() => handleSort('realized_cash_earnings')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Realized Cash Earnings</Text>
                        {getSortIcon('realized_cash_earnings')}
                      </Button>
                    </th>
                    <th className="px-6 py-3 text-center uppercase tracking-wider">
                      <Button
                        variant="ghost"
                        className="flex items-center justify-center space-x-1 hover:text-foreground p-0 h-auto"
                        onClick={() => handleSort('net_balance')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Amount Owed</Text>
                        {getSortIcon('net_balance')}
                      </Button>
                    </th>
                    <th className="px-6 py-3 text-center uppercase tracking-wider">
                      <Button
                        variant="ghost"
                        className="flex items-center justify-center space-x-1 hover:text-foreground p-0 h-auto"
                        onClick={() => handleSort('days_since_last_payment')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Days Since Last Payment</Text>
                        {getSortIcon('days_since_last_payment')}
                      </Button>
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {sortedPaymentSummary.map((player) => (
                    <tr key={player.player_id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Text variant="bodySmall" weight="medium">{player.player_name}</Text>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <Text variant="bodySmall">{formatCurrency(player.poker_net_winnings)}</Text>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <Text variant="bodySmall">{formatCurrency(player.total_paid)}</Text>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <Text variant="bodySmall">{formatCurrency(player.total_received)}</Text>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {(() => {
                          const realizedCashEarnings = player.total_received - player.total_paid;
                          return (
                            <Text
                              variant="bodySmall"
                              weight="medium"
                              color={
                                realizedCashEarnings > 0
                                  ? 'success'
                                  : realizedCashEarnings < 0
                                  ? 'destructive'
                                  : 'default'
                              }
                            >
                              {formatCurrency(realizedCashEarnings)}
                            </Text>
                          );
                        })()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {(() => {
                          const netBalance = (player.poker_net_winnings + player.total_paid) - player.total_received;
                          return (
                            <Text
                              variant="bodySmall"
                              weight="medium"
                              color={
                                netBalance > 0.005
                                  ? 'success'
                                  : netBalance < -0.005
                                  ? 'destructive'
                                  : 'default'
                              }
                            >
                              {formatCurrency(netBalance)}
                            </Text>
                          );
                        })()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <Text variant="bodySmall">
                          {player.days_since_last_payment !== null && player.days_since_last_payment !== undefined
                            ? `${player.days_since_last_payment} days`
                            : 'Never'
                          }
                        </Text>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Optimal Settlement Structure Tab */}
        {activeTab === 'settlements' && (
          <div className="bg-card text-card-foreground shadow rounded-lg border border-border">
            <div className="px-6 py-4 border-b border-border">
              <Heading variant="h2">Optimal Settlement Structure</Heading>
              <Text variant="bodySmall" color="muted">
                Required payments to settle all debts with minimum transactions
              </Text>
            </div>
            {settlements.length > 0 ? (
              <div className="p-6">
                <div className="space-y-6">
                  {Object.entries(groupedSettlements).map(([payerId, payerInfo]) => (
                    <div key={payerId} className="bg-muted/50 rounded-lg p-4 border border-border">
                      {/* Payer Header */}
                      <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-destructive/10 rounded-full flex items-center justify-center">
                            <DollarSign className="w-5 h-5 text-destructive" />
                          </div>
                          <div>
                            <Heading variant="h3">
                              {payerInfo.payer_name} owes
                            </Heading>
                          </div>
                        </div>
                        <div className="text-right">
                          <div>
                            <Heading variant="h4" color="destructive">{formatCurrency(payerInfo.total_owed)}</Heading>
                          </div>
                        </div>
                      </div>

                      {/* Individual Payments */}
                      <div className="space-y-0">
                        {payerInfo.payments.map((payment, paymentIndex) => (
                          <div key={paymentIndex}>
                            {paymentIndex > 0 && <hr className="border-border" />}
                            <div className="flex items-center justify-between py-3">
                              <div>
                                <Text variant="bodySmall" weight="bold">{payment.recipient_name}</Text>
                              </div>
                              <div className="flex items-center space-x-4">
                                <div className="text-right">
                                  <div>
                                    <Text variant="bodyLarge" weight="semibold" color="success">{formatCurrency(payment.amount)}</Text>
                                  </div>
                                </div>
                                {/* Only show Mark as Paid button for admin users */}
                                {canEdit && (
                                  <Button
                                    onClick={() => handleMarkSettlementPaid(payment)}
                                    disabled={submitLoading}
                                    size="sm"
                                    className="bg-black text-white hover:opacity-90 flex items-center space-x-1 text-xs px-2 py-1"
                                    title="Record this settlement as paid"
                                  >
                                    <DollarSign className="w-4 h-4" />
                                    <Text variant="caption">Mark as Paid</Text>
                                  </Button>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center">
                <Target className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <Text variant="body" color="muted">All players are settled up!</Text>
              </div>
            )}
          </div>
        )}

        {/* Payment History Tab */}
        {activeTab === 'history' && (
          <div className="bg-card text-card-foreground shadow rounded-lg border border-border">
            <div className="px-6 py-4 border-b border-border">
              <Heading variant="h2">Payment History</Heading>
              <Text variant="bodySmall" color="muted">
                All payment transactions
              </Text>
            </div>
            {paymentHistory.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-card border-b border-border">
                    <tr>
                      <th className="px-6 py-3 text-left uppercase tracking-wider">
                        <Text variant="caption" weight="medium" color="muted">Date</Text>
                      </th>
                      <th className="px-6 py-3 text-left uppercase tracking-wider">
                        <Text variant="caption" weight="medium" color="muted">Payer → Recipient</Text>
                      </th>
                      <th className="px-6 py-3 text-left uppercase tracking-wider">
                        <Text variant="caption" weight="medium" color="muted">Amount</Text>
                      </th>
                      <th className="px-6 py-3 text-left uppercase tracking-wider">
                        <Text variant="caption" weight="medium" color="muted">Method</Text>
                      </th>
                      <th className="px-6 py-3 text-left uppercase tracking-wider">
                        <Text variant="caption" weight="medium" color="muted">Notes</Text>
                      </th>
                      {/* Only show Actions column for admin users */}
                      {canEdit && (
                        <th className="px-6 py-3 text-left uppercase tracking-wider">
                          <Text variant="caption" weight="medium" color="muted">Actions</Text>
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="bg-card divide-y divide-border">
                    {paymentHistory.map((payment) => (
                      <tr key={payment.id}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <Text variant="bodySmall">{formatDate(payment.payment_date)}</Text>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <Text variant="bodySmall">{payment.payer_name} → {payment.recipient_name}</Text>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <Text variant="bodySmall" weight="medium" color="success">{formatCurrency(payment.amount)}</Text>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <Text variant="bodySmall">{payment.payment_method || '-'}</Text>
                        </td>
                        <td className="px-6 py-4">
                          <Text variant="bodySmall">{payment.notes || '-'}</Text>
                        </td>
                        {/* Only show Actions for admin users */}
                        {canEdit && (
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex space-x-2">
                              <Button
                                onClick={() => handleEditPayment(payment)}
                                variant="ghost"
                                size="icon-sm"
                                className="text-primary hover:text-primary/80 p-1"
                                title="Edit payment"
                              >
                                <Edit className="w-4 h-4" />
                              </Button>
                              <Button
                                onClick={() => handleDeletePayment(payment)}
                                variant="ghost"
                                size="icon-sm"
                                className="text-destructive hover:text-destructive/80 p-1"
                                title="Delete payment"
                                disabled={submitLoading}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center">
                <History className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <Text variant="body" color="muted">No payment history yet</Text>
              </div>
            )}
          </div>
        )}

        {/* Record Payment Tab - Only for admin users */}
        {activeTab === 'record' && canEdit && (
          <div className="bg-card text-card-foreground shadow rounded-lg border border-border">
            <div className="px-6 py-4 border-b border-border">
              <Heading variant="h2">Record Payment</Heading>
              <Text variant="bodySmall" color="muted">
                Record a payment between players
              </Text>
            </div>
            <form onSubmit={handleRecordPayment} className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Payer *
                  </Text>
                  <select
                    value={recordForm.payer_id}
                    onChange={(e) => setRecordForm({...recordForm, payer_id: e.target.value})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    required
                  >
                    <option value="">Select payer...</option>
                    {paymentSummary.map((player) => (
                      <option key={player.player_id} value={player.player_id}>
                        {player.player_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Recipient *
                  </Text>
                  <select
                    value={recordForm.recipient_id}
                    onChange={(e) => setRecordForm({...recordForm, recipient_id: e.target.value})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    required
                  >
                    <option value="">Select recipient...</option>
                    {paymentSummary
                      .filter(player => player.player_id !== recordForm.payer_id)
                      .map((player) => (
                      <option key={player.player_id} value={player.player_id}>
                        {player.player_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Amount * ($)
                  </Text>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={recordForm.amount}
                    onChange={(e) => setRecordForm({...recordForm, amount: e.target.value})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    placeholder="0.00"
                    required
                  />
                </div>

                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Payment Method
                  </Text>
                  <select
                    value={recordForm.payment_method}
                    onChange={(e) => setRecordForm({...recordForm, payment_method: e.target.value})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                  >
                    <option value="">Select method...</option>
                    <option value="Venmo">Venmo</option>
                    <option value="Zelle">Zelle</option>
                    <option value="Cash">Cash</option>
                    <option value="Bank Transfer">Bank Transfer</option>
                    <option value="PayPal">PayPal</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              <div>
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                  Notes
                </Text>
                <input
                  type="text"
                  value={recordForm.notes}
                  onChange={(e) => setRecordForm({...recordForm, notes: e.target.value})}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:ring-ring focus:border-ring placeholder:text-muted-foreground"
                  placeholder="Optional notes about the payment"
                />
              </div>

              <div>
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                  Reference ID
                </Text>
                <input
                  type="text"
                  value={recordForm.reference_id}
                  onChange={(e) => setRecordForm({...recordForm, reference_id: e.target.value})}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:ring-ring focus:border-ring placeholder:text-muted-foreground"
                  placeholder="Venmo/Zelle transaction ID"
                />
              </div>

              {!hasAdminSession && showAdminInput && (
                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Admin Code *
                  </Text>
                  <input
                    type="password"
                    value={manualAdminCode}
                    onChange={(e) => setManualAdminCode(e.target.value)}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    placeholder="Enter admin code"
                    required
                  />
                </div>
              )}

              <div className="flex justify-end space-x-3">
                <Button
                  type="button"
                  onClick={() => {
                    setRecordForm({
                      payer_id: '',
                      recipient_id: '',
                      amount: '',
                      payment_method: '',
                      notes: '',
                      reference_id: ''
                    });
                    setShowAdminInput(false);
                  }}
                  variant="outline"
                >
                  Clear
                </Button>
                <Button
                  type="submit"
                  disabled={submitLoading}
                  className="bg-black text-white hover:opacity-90"
                >
                  {submitLoading ? 'Recording...' : 'Record Payment'}
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Edit Payment Modal - Only for admin users */}
        {editingPayment && canEdit && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <Heading variant="h3">Edit Payment</Heading>
                <Button
                  onClick={() => setEditingPayment(null)}
                  variant="ghost"
                  size="icon-sm"
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-6 h-6" />
                </Button>
              </div>

              <form onSubmit={handleUpdatePayment} className="p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                      Payer *
                    </Text>
                    <select
                      value={editForm.payer_id}
                      onChange={(e) => setEditForm({...editForm, payer_id: e.target.value})}
                      className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                      required
                    >
                      <option value="">Select payer...</option>
                      {paymentSummary.map((player) => (
                        <option key={player.player_id} value={player.player_id}>
                          {player.player_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                      Recipient *
                    </Text>
                    <select
                      value={editForm.recipient_id}
                      onChange={(e) => setEditForm({...editForm, recipient_id: e.target.value})}
                      className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                      required
                    >
                      <option value="">Select recipient...</option>
                      {paymentSummary
                        .filter(player => player.player_id !== editForm.payer_id)
                        .map((player) => (
                        <option key={player.player_id} value={player.player_id}>
                          {player.player_name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                      Amount * ($)
                    </Text>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={editForm.amount}
                      onChange={(e) => setEditForm({...editForm, amount: e.target.value})}
                      className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                      placeholder="0.00"
                      required
                    />
                  </div>

                  <div>
                    <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                      Payment Method
                    </Text>
                    <select
                      value={editForm.payment_method}
                      onChange={(e) => setEditForm({...editForm, payment_method: e.target.value})}
                      className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    >
                      <option value="">Select method...</option>
                      <option value="Venmo">Venmo</option>
                      <option value="Zelle">Zelle</option>
                      <option value="Cash">Cash</option>
                      <option value="Bank Transfer">Bank Transfer</option>
                      <option value="PayPal">PayPal</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>

                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Notes
                  </Text>
                  <input
                    type="text"
                    value={editForm.notes}
                    onChange={(e) => setEditForm({...editForm, notes: e.target.value})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    placeholder="Optional notes about the payment"
                  />
                </div>

                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Reference ID
                  </Text>
                  <input
                    type="text"
                    value={editForm.reference_id}
                    onChange={(e) => setEditForm({...editForm, reference_id: e.target.value})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    placeholder="Venmo/Zelle transaction ID"
                  />
                </div>

                {!hasAdminSession && showAdminInput && (
                  <div>
                    <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                      Admin Code *
                    </Text>
                    <input
                      type="password"
                      value={manualAdminCode}
                      onChange={(e) => setManualAdminCode(e.target.value)}
                      className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                      placeholder="Enter admin code"
                      required
                    />
                  </div>
                )}

                <div className="flex justify-end space-x-3 pt-4">
                  <Button
                    type="button"
                    onClick={() => setEditingPayment(null)}
                    variant="outline"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={submitLoading}
                    className="bg-black text-white hover:opacity-90"
                  >
                    {submitLoading ? 'Updating...' : 'Update Payment'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Admin Code Input Modal */}
        {!hasAdminSession && showAdminInput && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border max-w-md w-full mx-4">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <Heading variant="h3">Admin Access Required</Heading>
                <Button
                  onClick={() => setShowAdminInput(false)}
                  variant="ghost"
                  size="icon-sm"
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-6 h-6" />
                </Button>
              </div>

              <div className="p-6">
                <Text variant="bodySmall" color="muted" className="mb-4">
                  Please enter your admin code to record this settlement payment.
                </Text>
                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Admin Code *
                  </Text>
                  <input
                    type="password"
                    value={manualAdminCode}
                    onChange={(e) => setManualAdminCode(e.target.value)}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    placeholder="Enter admin code"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        setShowAdminInput(false);
                      }
                    }}
                  />
                </div>
                <div className="flex justify-end space-x-3 mt-4">
                  <Button
                    onClick={() => setShowAdminInput(false)}
                    variant="outline"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={() => setShowAdminInput(false)}
                    disabled={!manualAdminCode}
                    className="bg-black text-white hover:opacity-90"
                  >
                    Continue
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal - Only for admin users */}
        {paymentToDelete && canEdit && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border max-w-md w-full mx-4">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <Heading variant="h3">Confirm Delete</Heading>
                <Button
                  onClick={() => setPaymentToDelete(null)}
                  variant="ghost"
                  size="icon-sm"
                  className="text-muted-foreground hover:text-foreground"
                  disabled={submitLoading}
                >
                  <X className="w-6 h-6" />
                </Button>
              </div>

              <div className="p-6">
                <div className="flex items-center mb-4">
                  <div className="flex-shrink-0 w-10 h-10 bg-destructive/20 rounded-full flex items-center justify-center">
                    <Trash2 className="w-6 h-6 text-destructive" />
                  </div>
                  <div className="ml-4">
                    <Text variant="bodyLarge" weight="medium" as="h4">Delete Payment</Text>
                    <Text variant="bodySmall" color="muted">This action cannot be undone.</Text>
                  </div>
                </div>

                <div className="bg-muted rounded-lg p-4 mb-4">
                  <div>
                    <Text variant="bodySmall" weight="medium" className="mb-1">Payment Details:</Text>
                    <div className="flex items-center justify-between">
                      <span>
                        <Text variant="bodySmall" weight="medium" color="primary" as="span">{paymentToDelete.payer_name}</Text>
                        <Text variant="bodySmall" color="muted" as="span" className="mx-2">→</Text>
                        <Text variant="bodySmall" weight="medium" color="success" as="span">{paymentToDelete.recipient_name}</Text>
                      </span>
                      <Text variant="bodyLarge" weight="bold">{formatCurrency(paymentToDelete.amount)}</Text>
                    </div>
                    {paymentToDelete.payment_method && (
                      <Text variant="caption" color="muted" className="mt-1">
                        via {paymentToDelete.payment_method}
                      </Text>
                    )}
                    {paymentToDelete.notes && (
                      <Text variant="caption" color="muted" className="mt-1">
                        Note: {paymentToDelete.notes}
                      </Text>
                    )}
                  </div>
                </div>

                {!hasAdminSession && showAdminInput && (
                  <div className="mb-4">
                    <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                      Admin Code *
                    </Text>
                    <input
                      type="password"
                      value={manualAdminCode}
                      onChange={(e) => setManualAdminCode(e.target.value)}
                      className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                      placeholder="Enter admin code"
                      required
                    />
                  </div>
                )}

                <div className="flex justify-end space-x-3">
                  <Button
                    type="button"
                    onClick={() => setPaymentToDelete(null)}
                    variant="outline"
                    disabled={submitLoading}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={confirmDeletePayment}
                    disabled={submitLoading}
                    variant="destructive"
                    className="flex items-center"
                  >
                    {submitLoading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4 mr-2" />
                        Delete Payment
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}