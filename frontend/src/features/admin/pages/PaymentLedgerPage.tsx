import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import AdminSessionStatus from '../../../components/AdminSessionStatus';
import { DollarSign, Users, TrendingUp, Plus, History, Target, ChevronUp, ChevronDown, HelpCircle } from 'lucide-react';

interface PlayerPaymentSummary {
  player_id: string;
  player_name: string;
  poker_net_winnings: number;
  total_paid: number;
  total_received: number;
  realized_cash_earnings?: number;  // Calculated field: received - paid
  net_balance?: number;  // Calculated field: (poker_winnings + paid_out) - received
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
  const { adminCode: sessionAdminCode, hasAdminSession } = useAdminSession();
  const [paymentSummary, setPaymentSummary] = useState<PlayerPaymentSummary[]>([]);
  const [settlements, setSettlements] = useState<SettlementSuggestion[]>([]);
  const [paymentHistory, setPaymentHistory] = useState<PaymentTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'summary' | 'settlements' | 'history' | 'record'>('summary');
  
  // Sorting state
  const [sortField, setSortField] = useState<keyof PlayerPaymentSummary | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  
  // Record payment form state
  const [showRecordForm, setShowRecordForm] = useState(false);
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

  const getAdminCode = () => {
    return hasAdminSession ? sessionAdminCode : manualAdminCode;
  };

  const fetchPaymentSummary = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/payments/summary`);
      setPaymentSummary(response.data.players);
    } catch (error) {
      console.error('Error fetching payment summary:', error);
    }
  };

  const fetchSettlements = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/payments/settlements`);
      setSettlements(response.data.settlements);
    } catch (error) {
      console.error('Error fetching settlements:', error);
    }
  };

  const fetchPaymentHistory = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/games/${publicCode}/payments/history?limit=20`);
      setPaymentHistory(response.data.transactions);
    } catch (error) {
      console.error('Error fetching payment history:', error);
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
      alert('Please fill in all required fields');
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
      setShowRecordForm(false);

      // Refresh all data
      await Promise.all([
        fetchPaymentSummary(),
        fetchSettlements(),
        fetchPaymentHistory()
      ]);

      alert('Payment recorded successfully!');
    } catch (error: any) {
      console.error('Error recording payment:', error);
      const errorMsg = error.response?.data?.error || 'Failed to record payment';
      alert(`Error: ${errorMsg}`);
    } finally {
      setSubmitLoading(false);
    }
  };

  const formatCurrency = (cents: number) => {
    return `$${(cents).toFixed(2)}`;
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading payment ledger...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <AdminSessionStatus className="mb-4" compact />
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">Payment Ledger</h1>
            <p className="text-sm text-gray-600">Game: {publicCode}</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('summary')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'summary'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Users className="w-4 h-4 inline mr-1" />
              Balance Summary
            </button>
            <button
              onClick={() => setActiveTab('settlements')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'settlements'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Target className="w-4 h-4 inline mr-1" />
              Optimal Settlement Structure
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'history'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <History className="w-4 h-4 inline mr-1" />
              Payment History
            </button>
            <button
              onClick={() => setActiveTab('record')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'record'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Plus className="w-4 h-4 inline mr-1" />
              Record Payment
            </button>
          </nav>
        </div>

        {/* Balance Summary Tab */}
        {activeTab === 'summary' && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Player Balance Summary</h2>
              <p className="text-sm text-gray-500">
                Payment data for all players
              </p>
            </div>
            <div className="overflow-x-auto overflow-y-visible">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <button
                        className="flex items-center space-x-1 hover:text-gray-700"
                        onClick={() => handleSort('player_name')}
                      >
                        <span>Player</span>
                        {getSortIcon('player_name')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <button
                        className="flex items-center space-x-1 hover:text-gray-700"
                        onClick={() => handleSort('poker_net_winnings')}
                      >
                        <span>Poker Winnings</span>
                        {getSortIcon('poker_net_winnings')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <button
                        className="flex items-center space-x-1 hover:text-gray-700"
                        onClick={() => handleSort('total_paid')}
                      >
                        <span>Paid Out</span>
                        {getSortIcon('total_paid')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <button
                        className="flex items-center space-x-1 hover:text-gray-700"
                        onClick={() => handleSort('total_received')}
                      >
                        <span>Received</span>
                        {getSortIcon('total_received')}
                      </button>
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <div className="flex items-center space-x-1">
                        <button
                          className="flex items-center space-x-1 hover:text-gray-700"
                          onClick={() => handleSort('realized_cash_earnings')}
                        >
                          <span>Realized Cash Earnings</span>
                          {getSortIcon('realized_cash_earnings')}
                        </button>
                        <div className="relative group">
                          <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                          <div className="absolute right-0 top-full mt-2 hidden group-hover:block z-50 w-64 p-3 text-sm text-gray-700 bg-white border border-gray-200 rounded-lg shadow-xl">
                            <div className="absolute -top-1 right-4 w-2 h-2 bg-white border-l border-t border-gray-200 rotate-45"></div>
                            Actual cash flow (received - paid out). Shows net cash position from payments made and received.
                          </div>
                        </div>
                      </div>
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <div className="flex items-center space-x-1">
                        <button
                          className="flex items-center space-x-1 hover:text-gray-700"
                          onClick={() => handleSort('net_balance')}
                        >
                          <span>Net Balance</span>
                          {getSortIcon('net_balance')}
                        </button>
                        <div className="relative group">
                          <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                          <div className="absolute right-0 top-full mt-2 hidden group-hover:block z-50 w-64 p-3 text-sm text-gray-700 bg-white border border-gray-200 rounded-lg shadow-xl">
                            <div className="absolute -top-1 right-4 w-2 h-2 bg-white border-l border-t border-gray-200 rotate-45"></div>
                            Amount owed to player (positive) or amount player owes (negative). Formula: (poker winnings + paid out) - received.
                          </div>
                        </div>
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sortedPaymentSummary.map((player) => (
                    <tr key={player.player_id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {player.player_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(player.poker_net_winnings)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(player.total_paid)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(player.total_received)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {(() => {
                          const realizedCashEarnings = player.total_received - player.total_paid;
                          return (
                            <span className={`font-medium ${
                              realizedCashEarnings > 0 
                                ? 'text-green-600' 
                                : realizedCashEarnings < 0 
                                ? 'text-red-600' 
                                : 'text-gray-900'
                            }`}>
                              {formatCurrency(realizedCashEarnings)}
                            </span>
                          );
                        })()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {(() => {
                          const netBalance = (player.poker_net_winnings + player.total_paid) - player.total_received;
                          return (
                            <span className={`font-medium ${
                              netBalance > 0 
                                ? 'text-green-600' 
                                : netBalance < 0 
                                ? 'text-red-600' 
                                : 'text-gray-900'
                            }`}>
                              {formatCurrency(netBalance)}
                            </span>
                          );
                        })()}
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
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Optimal Settlement Structure</h2>
              <p className="text-sm text-gray-500">
                Required payments to settle all debts with minimum transactions
              </p>
            </div>
            {settlements.length > 0 ? (
              <div className="p-6">
                <div className="space-y-4">
                  {settlements.map((settlement, index) => (
                    <div key={index} className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div className="flex-shrink-0">
                          <TrendingUp className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            <span className="text-blue-600">{settlement.payer_name}</span> should pay{' '}
                            <span className="text-green-600">{settlement.recipient_name}</span>
                          </p>
                        </div>
                      </div>
                      <div className="text-lg font-bold text-green-600">
                        {formatCurrency(settlement.amount)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center">
                <Target className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500">All players are settled up!</p>
              </div>
            )}
          </div>
        )}

        {/* Payment History Tab */}
        {activeTab === 'history' && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Payment History</h2>
              <p className="text-sm text-gray-500">
                Recent payment transactions
              </p>
            </div>
            {paymentHistory.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Date
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Payer → Recipient
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Amount
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Method
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Notes
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {paymentHistory.map((payment) => (
                      <tr key={payment.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {formatDate(payment.payment_date)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {payment.payer_name} → {payment.recipient_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-600">
                          {formatCurrency(payment.amount)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {payment.payment_method || '-'}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {payment.notes || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center">
                <History className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500">No payment history yet</p>
              </div>
            )}
          </div>
        )}

        {/* Record Payment Tab */}
        {activeTab === 'record' && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Record Payment</h2>
              <p className="text-sm text-gray-500">
                Record a payment between players
              </p>
            </div>
            <form onSubmit={handleRecordPayment} className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Payer *
                  </label>
                  <select
                    value={recordForm.payer_id}
                    onChange={(e) => setRecordForm({...recordForm, payer_id: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Recipient *
                  </label>
                  <select
                    value={recordForm.recipient_id}
                    onChange={(e) => setRecordForm({...recordForm, recipient_id: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Amount * ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={recordForm.amount}
                    onChange={(e) => setRecordForm({...recordForm, amount: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="0.00"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Payment Method
                  </label>
                  <select
                    value={recordForm.payment_method}
                    onChange={(e) => setRecordForm({...recordForm, payment_method: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
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
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <input
                  type="text"
                  value={recordForm.notes}
                  onChange={(e) => setRecordForm({...recordForm, notes: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Optional notes about the payment"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reference ID
                </label>
                <input
                  type="text"
                  value={recordForm.reference_id}
                  onChange={(e) => setRecordForm({...recordForm, reference_id: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Venmo/Zelle transaction ID"
                />
              </div>

              {!hasAdminSession && showAdminInput && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Admin Code *
                  </label>
                  <input
                    type="password"
                    value={manualAdminCode}
                    onChange={(e) => setManualAdminCode(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
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
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200"
                >
                  Clear
                </button>
                <button
                  type="submit"
                  disabled={submitLoading}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitLoading ? 'Recording...' : 'Record Payment'}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}