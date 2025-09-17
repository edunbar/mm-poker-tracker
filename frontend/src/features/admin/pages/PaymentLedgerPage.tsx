import axios from 'axios';
import { ChevronDown, ChevronUp, DollarSign, Edit, History, Plus, Target, Trash2, Users, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useToast } from '../../../contexts/ToastContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';

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
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/payments/summary`);
      setPaymentSummary(response.data.players);
    } catch (error) {
    }
  };


  const fetchSettlements = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/payments/settlements`);
      setSettlements(response.data.settlements);
    } catch (error) {
    }
  };

  const fetchPaymentHistory = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/payments/history`);
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

      await axios.post(`http://localhost:8000/api/games/${publicCode}/payments/record`, paymentData, {
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

      await axios.put(`http://localhost:8000/api/games/${publicCode}/payments/${editingPayment.id}`, paymentData, {
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
      await axios.delete(`http://localhost:8000/api/games/${publicCode}/payments/${paymentToDelete.id}`, {
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

      await axios.post(`http://localhost:8000/api/games/${publicCode}/payments/record`, paymentData, {
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

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
          <p className="mt-2 text-muted-foreground">Loading payment ledger...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Payment Ledger</h1>
            <p className="mt-2 text-muted-foreground">Track payments and settle debts</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-border mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('summary')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'summary'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <Users className="w-4 h-4 inline mr-1" />
              Balance Summary
            </button>
            <button
              onClick={() => setActiveTab('settlements')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'settlements'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <Target className="w-4 h-4 inline mr-1" />
              Optimal Settlement Structure
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'history'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <History className="w-4 h-4 inline mr-1" />
              Payment History
            </button>
            <button
              onClick={() => setActiveTab('record')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'record'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <Plus className="w-4 h-4 inline mr-1" />
              Record Payment
            </button>
          </nav>
        </div>

        {/* Balance Summary Tab */}
        {activeTab === 'summary' && (
          <div className="bg-card text-card-foreground shadow rounded-lg border border-border">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="text-lg font-medium text-foreground">Player Balance Summary</h2>
              <p className="text-sm text-muted-foreground">
                Payment data for all players
              </p>
            </div>
            <div className="overflow-x-auto overflow-y-visible">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-card border-b border-border">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      <button
                        className="flex items-center space-x-1 hover:text-foreground"
                        onClick={() => handleSort('player_name')}
                      >
                        <span>Player</span>
                        {getSortIcon('player_name')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      <button
                        className="flex items-center justify-center space-x-1 hover:text-foreground"
                        onClick={() => handleSort('poker_net_winnings')}
                      >
                        <span>Poker Winnings</span>
                        {getSortIcon('poker_net_winnings')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      <button
                        className="flex items-center justify-center space-x-1 hover:text-foreground"
                        onClick={() => handleSort('total_paid')}
                      >
                        <span>Paid Out</span>
                        {getSortIcon('total_paid')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      <button
                        className="flex items-center justify-center space-x-1 hover:text-foreground"
                        onClick={() => handleSort('total_received')}
                      >
                        <span>Received</span>
                        {getSortIcon('total_received')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      <button
                        className="flex items-center justify-center space-x-1 hover:text-foreground"
                        onClick={() => handleSort('realized_cash_earnings')}
                      >
                        <span>Realized Cash Earnings</span>
                        {getSortIcon('realized_cash_earnings')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      <button
                        className="flex items-center justify-center space-x-1 hover:text-foreground"
                        onClick={() => handleSort('net_balance')}
                      >
                        <span>Amount Owed</span>
                        {getSortIcon('net_balance')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      <button
                        className="flex items-center justify-center space-x-1 hover:text-foreground"
                        onClick={() => handleSort('days_since_last_payment')}
                      >
                        <span>Days Since Last Payment</span>
                        {getSortIcon('days_since_last_payment')}
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {sortedPaymentSummary.map((player) => (
                    <tr key={player.player_id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                        {player.player_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-center">
                        {formatCurrency(player.poker_net_winnings)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-center">
                        {formatCurrency(player.total_paid)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-center">
                        {formatCurrency(player.total_received)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                        {(() => {
                          const realizedCashEarnings = player.total_received - player.total_paid;
                          return (
                            <span className={`font-medium ${
                              realizedCashEarnings > 0
                                ? 'text-success'
                                : realizedCashEarnings < 0
                                ? 'text-destructive'
                                : 'text-foreground'
                            }`}>
                              {formatCurrency(realizedCashEarnings)}
                            </span>
                          );
                        })()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                        {(() => {
                          const netBalance = (player.poker_net_winnings + player.total_paid) - player.total_received;
                          return (
                            <span className={`font-medium ${
                              netBalance > 0.005
                                ? 'text-success'
                                : netBalance < -0.005
                                ? 'text-destructive'
                                : 'text-foreground'
                            }`}>
                              {formatCurrency(netBalance)}
                            </span>
                          );
                        })()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-center">
                        {player.days_since_last_payment !== null && player.days_since_last_payment !== undefined
                          ? `${player.days_since_last_payment} days`
                          : 'Never'
                        }
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
              <h2 className="text-lg font-medium text-foreground">Optimal Settlement Structure</h2>
              <p className="text-sm text-muted-foreground">
                Required payments to settle all debts with minimum transactions
              </p>
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
                            <h3 className="text-lg font-semibold text-foreground">
                              {payerInfo.payer_name} owes
                            </h3>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-destructive">
                            {formatCurrency(payerInfo.total_owed)}
                          </div>
                        </div>
                      </div>

                      {/* Individual Payments */}
                      <div className="space-y-0">
                        {payerInfo.payments.map((payment, paymentIndex) => (
                          <div key={paymentIndex}>
                            {paymentIndex > 0 && <hr className="border-border" />}
                            <div className="flex items-center justify-between py-3">
                              <div className="text-sm font-medium text-foreground">
                                <span className="font-bold text-foreground">{payment.recipient_name}</span>
                              </div>
                              <div className="flex items-center space-x-4">
                                <div className="text-right">
                                  <div className="text-lg font-semibold text-success">
                                    {formatCurrency(payment.amount)}
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleMarkSettlementPaid(payment)}
                                  disabled={submitLoading}
                                  className="px-2 py-1 text-xs font-medium text-white bg-black border border-transparent rounded-2xl hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
                                  title="Record this settlement as paid"
                                >
                                  <DollarSign className="w-4 h-4" />
                                  <span>Mark as Paid</span>
                                </button>
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
                <p className="text-muted-foreground">All players are settled up!</p>
              </div>
            )}
          </div>
        )}

        {/* Payment History Tab */}
        {activeTab === 'history' && (
          <div className="bg-card text-card-foreground shadow rounded-lg border border-border">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="text-lg font-medium text-foreground">Payment History</h2>
              <p className="text-sm text-muted-foreground">
                All payment transactions
              </p>
            </div>
            {paymentHistory.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-card border-b border-border">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Date
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Payer → Recipient
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Amount
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Method
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Notes
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-card divide-y divide-border">
                    {paymentHistory.map((payment) => (
                      <tr key={payment.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          {formatDate(payment.payment_date)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          {payment.payer_name} → {payment.recipient_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-success">
                          {formatCurrency(payment.amount)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          {payment.payment_method || '-'}
                        </td>
                        <td className="px-6 py-4 text-sm text-foreground">
                          {payment.notes || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleEditPayment(payment)}
                              className="text-primary hover:text-primary/80 p-1"
                              title="Edit payment"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeletePayment(payment)}
                              className="text-destructive hover:text-destructive/80 p-1"
                              title="Delete payment"
                              disabled={submitLoading}
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center">
                <History className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-muted-foreground">No payment history yet</p>
              </div>
            )}
          </div>
        )}

        {/* Record Payment Tab */}
        {activeTab === 'record' && (
          <div className="bg-card text-card-foreground shadow rounded-lg border border-border">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="text-lg font-medium text-foreground">Record Payment</h2>
              <p className="text-sm text-muted-foreground">
                Record a payment between players
              </p>
            </div>
            <form onSubmit={handleRecordPayment} className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Payer *
                  </label>
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
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Recipient *
                  </label>
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
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Amount * ($)
                  </label>
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
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Payment Method
                  </label>
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
                <label className="block text-sm font-medium text-foreground mb-1">
                  Notes
                </label>
                <input
                  type="text"
                  value={recordForm.notes}
                  onChange={(e) => setRecordForm({...recordForm, notes: e.target.value})}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:ring-ring focus:border-ring placeholder:text-muted-foreground"
                  placeholder="Optional notes about the payment"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Reference ID
                </label>
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
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Admin Code *
                  </label>
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
                <button
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
                  className="px-4 py-2 text-sm font-medium text-muted-foreground border border-input bg-background rounded-2xl hover:bg-accent"
                >
                  Clear
                </button>
                <button
                  type="submit"
                  disabled={submitLoading}
                  className="px-4 py-2 text-sm font-medium text-white bg-black border border-transparent rounded-2xl hover:opacity-90 disabled:opacity-50"
                >
                  {submitLoading ? 'Recording...' : 'Record Payment'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Edit Payment Modal */}
        {editingPayment && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <h3 className="text-lg font-medium text-foreground">Edit Payment</h3>
                <button
                  onClick={() => setEditingPayment(null)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              <form onSubmit={handleUpdatePayment} className="p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Payer *
                    </label>
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
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Recipient *
                    </label>
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
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Amount * ($)
                    </label>
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
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Payment Method
                    </label>
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
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Notes
                  </label>
                  <input
                    type="text"
                    value={editForm.notes}
                    onChange={(e) => setEditForm({...editForm, notes: e.target.value})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    placeholder="Optional notes about the payment"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Reference ID
                  </label>
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
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Admin Code *
                    </label>
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
                  <button
                    type="button"
                    onClick={() => setEditingPayment(null)}
                    className="px-4 py-2 text-sm font-medium text-muted-foreground border border-input bg-background rounded-2xl hover:bg-accent"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitLoading}
                    className="px-4 py-2 text-sm font-medium text-white bg-black border border-transparent rounded-2xl hover:opacity-90 disabled:opacity-50"
                  >
                    {submitLoading ? 'Updating...' : 'Update Payment'}
                  </button>
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
                <h3 className="text-lg font-medium text-foreground">Admin Access Required</h3>
                <button
                  onClick={() => setShowAdminInput(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              <div className="p-6">
                <p className="text-sm text-muted-foreground mb-4">
                  Please enter your admin code to record this settlement payment.
                </p>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Admin Code *
                  </label>
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
                  <button
                    onClick={() => setShowAdminInput(false)}
                    className="px-4 py-2 text-sm font-medium text-muted-foreground border border-input bg-background rounded-2xl hover:bg-accent"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => setShowAdminInput(false)}
                    disabled={!manualAdminCode}
                    className="px-4 py-2 text-sm font-medium text-white bg-black border border-transparent rounded-2xl hover:opacity-90 disabled:opacity-50"
                  >
                    Continue
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {paymentToDelete && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border max-w-md w-full mx-4">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <h3 className="text-lg font-medium text-foreground">Confirm Delete</h3>
                <button
                  onClick={() => setPaymentToDelete(null)}
                  className="text-muted-foreground hover:text-foreground"
                  disabled={submitLoading}
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <div className="flex-shrink-0 w-10 h-10 bg-destructive/20 rounded-full flex items-center justify-center">
                    <Trash2 className="w-6 h-6 text-destructive" />
                  </div>
                  <div className="ml-4">
                    <h4 className="text-lg font-medium text-foreground">Delete Payment</h4>
                    <p className="text-sm text-muted-foreground">This action cannot be undone.</p>
                  </div>
                </div>
                
                <div className="bg-muted rounded-lg p-4 mb-4">
                  <div className="text-sm text-foreground">
                    <div className="font-medium mb-1">Payment Details:</div>
                    <div className="flex items-center justify-between">
                      <span>
                        <span className="font-medium text-primary">{paymentToDelete.payer_name}</span>
                        <span className="mx-2 text-muted-foreground">→</span>
                        <span className="font-medium text-success">{paymentToDelete.recipient_name}</span>
                      </span>
                      <span className="font-bold text-lg">{formatCurrency(paymentToDelete.amount)}</span>
                    </div>
                    {paymentToDelete.payment_method && (
                      <div className="text-xs text-muted-foreground mt-1">
                        via {paymentToDelete.payment_method}
                      </div>
                    )}
                    {paymentToDelete.notes && (
                      <div className="text-xs text-muted-foreground mt-1">
                        Note: {paymentToDelete.notes}
                      </div>
                    )}
                  </div>
                </div>

                {!hasAdminSession && showAdminInput && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Admin Code *
                    </label>
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
                  <button
                    type="button"
                    onClick={() => setPaymentToDelete(null)}
                    className="px-4 py-2 text-sm font-medium text-muted-foreground border border-input bg-background rounded-2xl hover:bg-accent"
                    disabled={submitLoading}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmDeletePayment}
                    disabled={submitLoading}
                    className="px-4 py-2 text-sm font-medium text-destructive-foreground bg-destructive border border-transparent rounded-2xl hover:bg-destructive/90 disabled:opacity-50 flex items-center"
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
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}