import axios from 'axios';
import { AlertTriangle, Bell, ChevronDown, ChevronUp, CreditCard, DollarSign, Edit, History, Plus, Star, Target, Trash2, Users, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '../../../api/client';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useAuth } from '../../../contexts/AuthContext';
import { useToast } from '../../../contexts/ToastContext';
import { useGameTitle } from '../../../shared/hooks/useGameTitle';
import { Button } from '../../../shared/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../../../shared/ui/tooltip';
import { Heading, Text } from '../../../shared/ui/typography';
import { AlertSettings } from '../../admin/components/AlertSettings';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface PlayerPaymentSummary {
  player_id: string;
  player_name: string;
  poker_net_winnings: number;
  total_paid: number;
  total_received: number;
  balance: number;  // Payment balance from API
  realized_earnings: number;  // Realized cash earnings from API
  days_since_last_payment?: number | null;  // Days since balance became negative
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

interface ApiError {
  response?: {
    data?: {
      error?: string;
    };
  };
}

interface PlayerPaymentMethod {
  id: string;
  payment_method: string;
  payment_address: string;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}

interface PlayerWithMethods {
  player_id: string;
  player_name: string;
  methods: PlayerPaymentMethod[];
}

export default function PaymentLedgerPage() {
  const { publicCode } = useParams<{ publicCode: string }>();
  const { title: _title } = useGameTitle(publicCode || '');
  const { getAdminCode, hasAdminSession: hasAdminSessionForGame } = useAdminSession();
  const sessionAdminCode = getAdminCode(publicCode || '');
  const hasAdminSession = hasAdminSessionForGame(publicCode || '');
  const { isAuthenticated } = useAuth();
  const { showSuccess, showError } = useToast();
  const [paymentSummary, setPaymentSummary] = useState<PlayerPaymentSummary[]>([]);
  const [settlements, setSettlements] = useState<SettlementSuggestion[]>([]);
  const [paymentHistory, setPaymentHistory] = useState<PaymentTransaction[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PlayerWithMethods[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'summary' | 'settlements' | 'history' | 'record' | 'alerts' | 'methods'>('summary');
  const [playersWithViolations, setPlayersWithViolations] = useState<Map<string, string>>(new Map());

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

  // Payment method modal state
  const [showMethodModal, setShowMethodModal] = useState(false);
  const [editingMethod, setEditingMethod] = useState<PlayerPaymentMethod | null>(null);
  const [methodPlayerId, setMethodPlayerId] = useState<string>('');
  const [editingPlayerMethods, setEditingPlayerMethods] = useState<string | null>(null);
  const [methodForm, setMethodForm] = useState({
    payment_method: '',
    payment_address: '',
    is_primary: false
  });
  const [methodToDelete, setMethodToDelete] = useState<PlayerPaymentMethod | null>(null);

  const getEffectiveAdminCode = () => {
    return hasAdminSession ? sessionAdminCode : manualAdminCode;
  };

  const getHeaders = () => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };

    // Only send X-Admin-Code when not authenticated
    const adminCode = getEffectiveAdminCode();
    if (!isAuthenticated && adminCode) {
      headers['X-Admin-Code'] = adminCode;
    }

    return headers;
  };

  const fetchPaymentSummary = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/games/${publicCode}/payments/summary`);
      setPaymentSummary(response.data.players);
    } catch (error) {
      // Silently handle error
    }
  }, [publicCode]);

  const fetchSettlements = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/games/${publicCode}/payments/settlements`);
      setSettlements(response.data.settlements);
    } catch (error) {
      // Silently handle error
    }
  }, [publicCode]);

  const fetchPaymentHistory = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/games/${publicCode}/payments/history`);
      setPaymentHistory(response.data.transactions);
    } catch (error) {
      // Silently handle error
    }
  }, [publicCode]);

  const fetchAlertStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/alerts/status`);
      const playerAlertsData = response.data.player_alerts || [];
      const violationsMap = new Map<string, string>();

      playerAlertsData
        .filter((alert: { violation_count: number }) => alert.violation_count > 0)
        .forEach((alert: {
          player_id: string;
          player_name: string;
          violations: Array<{
            rule_type: string;
            threshold_value: number;
            current_value: number;
            threshold_value_dollars?: number;
            current_value_dollars?: number;
          }>
        }) => {
          const violationMessages = alert.violations.map(v => {
            if (v.rule_type === 'amount_threshold') {
              return `Owes $${v.current_value_dollars?.toFixed(2)} (threshold: $${v.threshold_value_dollars?.toFixed(2)})`;
            } else if (v.rule_type === 'days_overdue') {
              return `${v.current_value} days overdue (threshold: ${v.threshold_value} days)`;
            }
            return '';
          }).filter(Boolean);

          if (violationMessages.length > 0) {
            violationsMap.set(alert.player_id, violationMessages.join(', '));
          }
        });

      setPlayersWithViolations(violationsMap);
    } catch (error) {
      // Silently handle error - alerts are optional feature
    }
  }, [publicCode]);

  const fetchPaymentMethods = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/games/${publicCode}/all-payment-methods`);
      setPaymentMethods(response.data);
    } catch (error) {
      // Silently handle error
    }
  }, [publicCode]);


  useEffect(() => {
    if (publicCode) {
      setLoading(true);
      Promise.all([
        fetchPaymentSummary(),
        fetchSettlements(),
        fetchPaymentHistory(),
        fetchAlertStatus(),
        fetchPaymentMethods()
      ]).finally(() => {
        setLoading(false);
      });
    }
  }, [publicCode, fetchPaymentSummary, fetchSettlements, fetchPaymentHistory, fetchAlertStatus, fetchPaymentMethods]);

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();

    const adminCode = getEffectiveAdminCode();
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

      await apiClient.post(`/api/games/${publicCode}/payments`, paymentData, {
        headers: getHeaders()
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
        fetchPaymentHistory(),
        fetchAlertStatus()
      ]);

      showSuccess('Payment Recorded', 'Payment recorded successfully!');
    } catch (error) {
      const errorMsg = (error as ApiError).response?.data?.error || 'Failed to record payment';
      showError('Payment Error', errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleEditPayment = (payment: PaymentTransaction) => {
    // Find the payer and recipient from paymentSummary
    const payer = (paymentSummary || []).find(p => p.player_name === payment.payer_name);
    const recipient = (paymentSummary || []).find(p => p.player_name === payment.recipient_name);

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

    const adminCode = getEffectiveAdminCode();
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

      await apiClient.put(`/api/games/${publicCode}/payments/${editingPayment.id}`, paymentData, {
        headers: getHeaders()
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
        fetchPaymentHistory(),
        fetchAlertStatus()
      ]);

      showSuccess('Payment Updated', 'Payment updated successfully!');
    } catch (error) {
      const errorMsg = (error as ApiError).response?.data?.error || 'Failed to update payment';
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

    const adminCode = getEffectiveAdminCode();
    if (!adminCode) {
      setShowAdminInput(true);
      return;
    }

    setSubmitLoading(true);

    try {
      await apiClient.delete(`/api/games/${publicCode}/payments/${paymentToDelete.id}`, {
        headers: getHeaders()
      });

      // Close modal and refresh data
      setPaymentToDelete(null);
      await Promise.all([
        fetchPaymentSummary(),
        fetchSettlements(),
        fetchPaymentHistory(),
        fetchAlertStatus()
      ]);

      showSuccess('Payment Deleted', 'Payment deleted successfully!');
    } catch (error) {
      const errorMsg = (error as ApiError).response?.data?.error || 'Failed to delete payment';
      showError('Delete Error', errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleMarkSettlementPaid = async (settlement: SettlementSuggestion) => {
    const adminCode = getEffectiveAdminCode();
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

      await apiClient.post(`/api/games/${publicCode}/payments`, paymentData, {
        headers: getHeaders()
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
        fetchPaymentHistory(),
        fetchAlertStatus()
      ]);

      showSuccess(
        'Settlement Recorded',
        `Payment recorded: ${settlement.payer_name} paid ${settlement.recipient_name} ${formatCurrency(settlement.amount)}`
      );
    } catch (error) {
      const errorMsg = (error as ApiError).response?.data?.error || 'Failed to record settlement payment';
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

  // Payment method handlers
  const handleAddMethod = (playerId: string) => {
    setMethodPlayerId(playerId);
    setEditingMethod(null);
    setMethodForm({
      payment_method: '',
      payment_address: '',
      is_primary: false
    });
    setShowMethodModal(true);
  };

  const handleEditMethod = (playerId: string, method: PlayerPaymentMethod) => {
    setMethodPlayerId(playerId);
    setEditingMethod(method);
    setMethodForm({
      payment_method: method.payment_method,
      payment_address: method.payment_address,
      is_primary: method.is_primary
    });
    setShowMethodModal(true);
  };

  const handleSaveMethod = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!methodForm.payment_method || !methodForm.payment_address) {
      showError('Validation Error', 'Please fill in payment method and address');
      return;
    }

    setSubmitLoading(true);

    try {
      if (editingMethod) {
        // Update existing method
        await axios.put(
          `${API_BASE_URL}/api/games/players/${methodPlayerId}/payment-methods/${editingMethod.id}`,
          methodForm
        );
        showSuccess('Method Updated', 'Payment method updated successfully');
      } else {
        // Add new method
        await axios.post(
          `${API_BASE_URL}/api/games/players/${methodPlayerId}/payment-methods`,
          methodForm
        );
        showSuccess('Method Added', 'Payment method added successfully');
      }

      // Refresh payment methods
      await fetchPaymentMethods();
      setShowMethodModal(false);
    } catch (error) {
      const errorMsg = (error as ApiError).response?.data?.error || 'Failed to save payment method';
      showError('Error', errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleSetPrimary = async (playerId: string, methodId: string) => {
    setSubmitLoading(true);
    try {
      await axios.post(
        `${API_BASE_URL}/api/games/players/${playerId}/payment-methods/${methodId}/set-primary`
      );
      showSuccess('Primary Set', 'Primary payment method updated');
      await fetchPaymentMethods();
    } catch (error) {
      const errorMsg = (error as ApiError).response?.data?.error || 'Failed to set primary method';
      showError('Error', errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  const confirmDeleteMethod = async () => {
    if (!methodToDelete) return;

    setSubmitLoading(true);
    try {
      await axios.delete(
        `${API_BASE_URL}/api/games/players/${methodPlayerId}/payment-methods/${methodToDelete.id}`
      );
      showSuccess('Method Deleted', 'Payment method deleted successfully');
      await fetchPaymentMethods();
      setMethodToDelete(null);
    } catch (error) {
      const errorMsg = (error as ApiError).response?.data?.error || 'Failed to delete payment method';
      showError('Error', errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleSort = (field: keyof PlayerPaymentSummary) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedPaymentSummary = [...(paymentSummary || [])].sort((a, b) => {
    if (!sortField) return 0;

    let aValue: string | number | null | undefined, bValue: string | number | null | undefined;

    // Direct field access - no mapping needed
    aValue = a[sortField];
    bValue = b[sortField];

    // Handle null/undefined values
    if ((aValue === null || aValue === undefined) && (bValue === null || bValue === undefined)) return 0;
    if (aValue === null || aValue === undefined) return 1;
    if (bValue === null || bValue === undefined) return -1;

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

  // Get primary payment method for a player
  const getPrimaryPaymentMethod = (playerId: string): PlayerPaymentMethod | null => {
    const playerMethods = paymentMethods.find(pm => pm.player_id === playerId);
    if (!playerMethods || !playerMethods.methods || playerMethods.methods.length === 0) {
      return null;
    }
    return playerMethods.methods.find(m => m.is_primary) || null;
  };

  // Group settlements by payer
  const groupedSettlements = (settlements || []).reduce((acc, settlement) => {
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
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-8">
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
          <nav className="-mb-px flex flex-col sm:flex-row sm:space-x-8 space-y-2 sm:space-y-0">
            <Button
              onClick={() => setActiveTab('summary')}
              variant="ghost"
              className={`py-2 px-3 sm:px-1 border-b-2 sm:border-b-2 border-l-4 sm:border-l-0 font-medium text-sm rounded-none w-full sm:w-auto justify-start sm:justify-center ${
                activeTab === 'summary'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <Users className="w-4 h-4 inline mr-2" />
              Balance Summary
            </Button>
            <Button
              onClick={() => setActiveTab('settlements')}
              variant="ghost"
              className={`py-2 px-3 sm:px-1 border-b-2 sm:border-b-2 border-l-4 sm:border-l-0 font-medium text-sm rounded-none w-full sm:w-auto justify-start sm:justify-center ${
                activeTab === 'settlements'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <Target className="w-4 h-4 inline mr-2" />
              Optimal Settlement Structure
            </Button>
            <Button
              onClick={() => setActiveTab('history')}
              variant="ghost"
              className={`py-2 px-3 sm:px-1 border-b-2 sm:border-b-2 border-l-4 sm:border-l-0 font-medium text-sm rounded-none w-full sm:w-auto justify-start sm:justify-center ${
                activeTab === 'history'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <History className="w-4 h-4 inline mr-2" />
              Payment History
            </Button>
            <Button
              onClick={() => setActiveTab('methods')}
              variant="ghost"
              className={`py-2 px-3 sm:px-1 border-b-2 sm:border-b-2 border-l-4 sm:border-l-0 font-medium text-sm rounded-none w-full sm:w-auto justify-start sm:justify-center ${
                activeTab === 'methods'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <CreditCard className="w-4 h-4 inline mr-2" />
              Payment Methods
            </Button>
            {/* Only show Record Payment and Alerts tabs for admin users */}
            {canEdit && (
              <>
                <Button
                  onClick={() => setActiveTab('record')}
                  variant="ghost"
                  className={`py-2 px-3 sm:px-1 border-b-2 sm:border-b-2 border-l-4 sm:border-l-0 font-medium text-sm rounded-none w-full sm:w-auto justify-start sm:justify-center ${
                    activeTab === 'record'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                  }`}
                >
                  <Plus className="w-4 h-4 inline mr-2" />
                  Record Payment
                </Button>
                <Button
                  onClick={() => setActiveTab('alerts')}
                  variant="ghost"
                  className={`py-2 px-3 sm:px-1 border-b-2 sm:border-b-2 border-l-4 sm:border-l-0 font-medium text-sm rounded-none w-full sm:w-auto justify-start sm:justify-center ${
                    activeTab === 'alerts'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                  }`}
                >
                  <Bell className="w-4 h-4 inline mr-2" />
                  Alerts
                </Button>
              </>
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

            {/* Desktop Table View */}
            <div className="hidden md:block overflow-x-auto overflow-y-visible">
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
                        onClick={() => handleSort('realized_earnings')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Realized Cash Earnings</Text>
                        {getSortIcon('realized_earnings')}
                      </Button>
                    </th>
                    <th className="px-6 py-3 text-center uppercase tracking-wider">
                      <Button
                        variant="ghost"
                        className="flex items-center justify-center space-x-1 hover:text-foreground p-0 h-auto"
                        onClick={() => handleSort('balance')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Amount Owed</Text>
                        {getSortIcon('balance')}
                      </Button>
                    </th>
                    <th className="px-6 py-3 text-center uppercase tracking-wider">
                      <Button
                        variant="ghost"
                        className="flex items-center justify-center space-x-1 hover:text-foreground p-0 h-auto"
                        onClick={() => handleSort('days_since_last_payment')}
                      >
                        <Text variant="caption" weight="medium" color="muted">Days Balance Negative</Text>
                        {getSortIcon('days_since_last_payment')}
                      </Button>
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {sortedPaymentSummary.map((player) => (
                    <tr key={player.player_id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {playersWithViolations.has(player.player_id) && (
                            <Tooltip>
                              <TooltipTrigger>
                                <AlertTriangle className="w-4 h-4 text-destructive" />
                              </TooltipTrigger>
                              <TooltipContent className="left-0 translate-x-0">
                                {playersWithViolations.get(player.player_id)}
                              </TooltipContent>
                            </Tooltip>
                          )}
                          <Text variant="bodySmall" weight="medium">{player.player_name}</Text>
                        </div>
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
                        <Text
                          variant="bodySmall"
                          weight="medium"
                          color={
                            player.realized_earnings > 0
                              ? 'success'
                              : player.realized_earnings < 0
                              ? 'destructive'
                              : 'default'
                          }
                        >
                          {formatCurrency(player.realized_earnings)}
                        </Text>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <Text
                          variant="bodySmall"
                          weight="medium"
                          color={
                            player.balance > 0.005
                              ? 'success'
                              : player.balance < -0.005
                              ? 'destructive'
                              : 'default'
                          }
                        >
                          {formatCurrency(player.balance)}
                        </Text>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <Text variant="bodySmall">
                          {player.days_since_last_payment !== null && player.days_since_last_payment !== undefined
                            ? `${player.days_since_last_payment} days`
                            : '–'
                          }
                        </Text>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Card View */}
            <div className="md:hidden divide-y divide-border">
              {sortedPaymentSummary.map((player) => {
                return (
                  <div key={player.player_id} className="p-4">
                    <div className="mb-3 flex items-center gap-2">
                      {playersWithViolations.has(player.player_id) && (
                        <Tooltip>
                          <TooltipTrigger>
                            <AlertTriangle className="w-5 h-5 text-destructive" />
                          </TooltipTrigger>
                          <TooltipContent className="left-0 translate-x-0">
                            {playersWithViolations.get(player.player_id)}
                          </TooltipContent>
                        </Tooltip>
                      )}
                      <Text variant="bodyLarge" weight="semibold">{player.player_name}</Text>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <Text variant="bodySmall" color="muted">Poker Winnings</Text>
                        <Text variant="bodySmall" weight="medium">{formatCurrency(player.poker_net_winnings)}</Text>
                      </div>

                      <div className="flex justify-between">
                        <Text variant="bodySmall" color="muted">Paid Out</Text>
                        <Text variant="bodySmall" weight="medium">{formatCurrency(player.total_paid)}</Text>
                      </div>

                      <div className="flex justify-between">
                        <Text variant="bodySmall" color="muted">Received</Text>
                        <Text variant="bodySmall" weight="medium">{formatCurrency(player.total_received)}</Text>
                      </div>

                      <div className="flex justify-between pt-2 border-t border-border">
                        <Text variant="bodySmall" color="muted" weight="medium">Realized Cash Earnings</Text>
                        <Text
                          variant="bodySmall"
                          weight="bold"
                          color={
                            player.realized_earnings > 0
                              ? 'success'
                              : player.realized_earnings < 0
                              ? 'destructive'
                              : 'default'
                          }
                        >
                          {formatCurrency(player.realized_earnings)}
                        </Text>
                      </div>

                      <div className="flex justify-between">
                        <Text variant="bodySmall" color="muted" weight="medium">Amount Owed</Text>
                        <Text
                          variant="bodySmall"
                          weight="bold"
                          color={
                            player.balance > 0.005
                              ? 'success'
                              : player.balance < -0.005
                              ? 'destructive'
                              : 'default'
                          }
                        >
                          {formatCurrency(player.balance)}
                        </Text>
                      </div>

                      <div className="flex justify-between">
                        <Text variant="bodySmall" color="muted">Days Balance Negative</Text>
                        <Text variant="bodySmall">
                          {player.days_since_last_payment !== null && player.days_since_last_payment !== undefined
                            ? `${player.days_since_last_payment} days`
                            : '–'
                          }
                        </Text>
                      </div>
                    </div>
                  </div>
                );
              })}
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
            {(settlements || []).length > 0 ? (
              <div className="p-2">
                {/* Desktop View - Grouped by Payer */}
                <div className="hidden md:block space-y-4">
                  {Object.entries(groupedSettlements).map(([payerId, payerInfo]) => (
                    <div key={payerId} className="border border-border rounded-lg overflow-hidden shadow-sm">
                      {/* Payer Header */}
                      <div className="bg-muted/50 px-4 py-3 flex items-center justify-between border-b border-border">
                        <div className="flex items-center gap-2">
                          <Text variant="body" weight="bold">{payerInfo.payer_name} owes</Text>
                        </div>
                        <Text variant="bodyLarge" weight="bold" color="destructive">
                          {formatCurrency(payerInfo.total_owed)}
                        </Text>
                      </div>

                      {/* Payments Table */}
                      <table className="min-w-full">
                        <tbody className="bg-card divide-y divide-border">
                          {payerInfo.payments.map((payment, index) => {
                            const primaryMethod = getPrimaryPaymentMethod(payment.recipient_id);
                            return (
                              <tr key={index} className="hover:bg-muted/20">
                                <td className="px-4 py-3">
                                  <div className="flex items-center gap-2">
                                    <Text variant="body" weight="medium">{payment.recipient_name}</Text>
                                    {primaryMethod ? (
                                      <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs border border-primary bg-primary/10 text-primary whitespace-nowrap">
                                        <span className="font-medium">{primaryMethod.payment_method}:</span>
                                        <span className="text-muted-foreground">{primaryMethod.payment_address}</span>
                                      </div>
                                    ) : (
                                      <Text variant="caption" color="muted" className="italic">(No payment method)</Text>
                                    )}
                                  </div>
                                </td>
                                <td className="px-4 py-3 text-right whitespace-nowrap w-32">
                                  <Text variant="body" weight="bold" color="success">
                                    {formatCurrency(payment.amount)}
                                  </Text>
                                </td>
                                {canEdit && (
                                  <td className="px-4 py-3 text-right whitespace-nowrap w-36">
                                    <Button
                                      onClick={() => handleMarkSettlementPaid(payment)}
                                      disabled={submitLoading}
                                      size="sm"
                                      variant="ghost"
                                      className="h-7 px-2 text-xs"
                                      title="Record this settlement as paid"
                                    >
                                      <DollarSign className="w-3 h-3 mr-1" />
                                      Mark as Paid
                                    </Button>
                                  </td>
                                )}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>

                {/* Mobile View - Grouped by Payer */}
                <div className="md:hidden space-y-4">
                  {Object.entries(groupedSettlements).map(([payerId, payerInfo]) => (
                    <div key={payerId} className="border border-border rounded-lg overflow-hidden shadow-sm">
                      {/* Payer Header */}
                      <div className="bg-muted/50 px-3 py-3 border-b border-border">
                        <div className="flex items-center justify-between">
                          <Text variant="body" weight="bold">{payerInfo.payer_name} owes</Text>
                          <Text variant="bodyLarge" weight="bold" color="destructive">
                            {formatCurrency(payerInfo.total_owed)}
                          </Text>
                        </div>
                      </div>

                      {/* Payments List */}
                      <div className="divide-y divide-border">
                        {payerInfo.payments.map((payment, index) => {
                          const primaryMethod = getPrimaryPaymentMethod(payment.recipient_id);
                          return (
                            <div key={index} className="p-3">
                              <div className="mb-2">
                                <Text variant="body" weight="medium">{payment.recipient_name}</Text>
                                {primaryMethod ? (
                                  <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs border border-primary bg-primary/10 text-primary w-fit mt-1 whitespace-nowrap">
                                    <span className="font-medium">{primaryMethod.payment_method}:</span>
                                    <span className="text-muted-foreground">{primaryMethod.payment_address}</span>
                                  </div>
                                ) : (
                                  <Text variant="caption" color="muted" className="italic block mt-1">(No payment method)</Text>
                                )}
                              </div>
                              <div className="flex items-center justify-between pt-2 border-t border-border">
                                <Text variant="bodyLarge" weight="bold" color="success">
                                  {formatCurrency(payment.amount)}
                                </Text>
                                {canEdit && (
                                  <Button
                                    onClick={() => handleMarkSettlementPaid(payment)}
                                    disabled={submitLoading}
                                    size="sm"
                                    className="h-8 px-3 text-xs"
                                    title="Record this settlement as paid"
                                  >
                                    <DollarSign className="w-3 h-3 mr-1" />
                                    Mark as Paid
                                  </Button>
                                )}
                              </div>
                            </div>
                          );
                        })}
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
            {(paymentHistory || []).length > 0 ? (
              <>
                {/* Mobile Card View */}
                <div className="md:hidden divide-y divide-border">
                  {(paymentHistory || []).map((payment) => (
                    <div key={payment.id} className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <Text variant="caption" color="muted">{formatDate(payment.payment_date)}</Text>
                          <Text variant="bodyLarge" weight="bold" color="success" className="mt-1">
                            {formatCurrency(payment.amount)}
                          </Text>
                        </div>
                      </div>

                      <div className="space-y-2 mb-3">
                        <div className="flex items-center gap-2">
                          <Text variant="body">{payment.payer_name}</Text>
                          <Text variant="body" color="muted">→</Text>
                          <Text variant="body">{payment.recipient_name}</Text>
                        </div>

                        {payment.payment_method && (
                          <div className="flex items-center gap-2">
                            <Text variant="bodySmall" color="muted">Method:</Text>
                            <Text variant="bodySmall">{payment.payment_method}</Text>
                          </div>
                        )}

                        {payment.notes && (
                          <div>
                            <Text variant="bodySmall" color="muted">Notes:</Text>
                            <Text variant="bodySmall" className="mt-1">{payment.notes}</Text>
                          </div>
                        )}
                      </div>

                      {canEdit && (
                        <div className="flex gap-2 pt-3 border-t border-border">
                          <Button
                            onClick={() => handleEditPayment(payment)}
                            variant="outline"
                            className="flex-1 min-h-[44px]"
                          >
                            <Edit className="w-4 h-4 mr-2" />
                            Edit
                          </Button>
                          <Button
                            onClick={() => handleDeletePayment(payment)}
                            variant="outline"
                            className="flex-1 min-h-[44px] text-destructive hover:text-destructive border-destructive/50"
                            disabled={submitLoading}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Desktop Table View */}
                <div className="hidden md:block overflow-x-auto -mx-4 sm:mx-0">
                  <div className="inline-block min-w-full align-middle px-4 sm:px-0">
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
                      {(paymentHistory || []).map((payment) => (
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
                </div>
              </>
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
            <form onSubmit={handleRecordPayment} className="p-4 md:p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                    {(paymentSummary || []).map((player) => (
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
                    {(paymentSummary || [])
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

              <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
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
                  className="w-full sm:w-auto min-h-[44px]"
                >
                  Clear
                </Button>
                <Button
                  type="submit"
                  disabled={submitLoading}
                  className="bg-black text-white hover:opacity-90 w-full sm:w-auto min-h-[44px]"
                >
                  {submitLoading ? 'Recording...' : 'Record Payment'}
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Alerts Tab - Only for admin users */}
        {activeTab === 'alerts' && canEdit && (
          <AlertSettings publicCode={publicCode || ''} />
        )}

        {/* Payment Methods Tab */}
        {activeTab === 'methods' && (
          <div className="bg-card text-card-foreground shadow rounded-lg border border-border">
            <div className="px-6 py-4 border-b border-border">
              <Heading variant="h2">Payment Methods</Heading>
              <Text variant="bodySmall" color="muted">
                View and manage payment methods for all players
              </Text>
            </div>

            {(paymentMethods || []).length > 0 ? (
              <div className="p-4">
                {/* Desktop Table View */}
                <div className="hidden md:block overflow-x-auto">
                  <table className="min-w-full divide-y divide-border">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-2 text-left">
                          <Text variant="caption" weight="medium" color="muted">Player</Text>
                        </th>
                        <th className="px-4 py-2 text-left">
                          <Text variant="caption" weight="medium" color="muted">Payment Methods</Text>
                        </th>
                        <th className="px-4 py-2 text-right">
                          <Text variant="caption" weight="medium" color="muted">Actions</Text>
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-card divide-y divide-border">
                      {paymentMethods.map((playerData) => (
                        <>
                          <tr key={playerData.player_id} className="hover:bg-muted/30">
                            <td className="px-4 py-2 whitespace-nowrap">
                              <Text variant="bodySmall" weight="medium">{playerData.player_name}</Text>
                            </td>
                            <td className="px-4 py-2">
                              {playerData.methods.length > 0 ? (
                                <div className="flex flex-wrap gap-1.5">
                                  {playerData.methods.map((method) => (
                                    <div
                                      key={method.id}
                                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${
                                        method.is_primary
                                          ? 'border-primary bg-primary/10 text-primary'
                                          : 'border-border bg-muted/50'
                                      }`}
                                    >
                                      {method.is_primary && (
                                        <Star className="w-3 h-3 fill-primary text-primary" />
                                      )}
                                      <span className="font-medium">{method.payment_method}:</span>
                                      <span className="text-muted-foreground">{method.payment_address}</span>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <Text variant="caption" color="muted">No methods added</Text>
                              )}
                            </td>
                            <td className="px-4 py-2 text-right whitespace-nowrap">
                              <div className="flex items-center justify-end gap-1">
                                <Button
                                  onClick={() => handleAddMethod(playerData.player_id)}
                                  size="sm"
                                  variant="ghost"
                                  className="h-7 px-2 text-xs"
                                >
                                  <Plus className="w-3 h-3 mr-1" />
                                  Add
                                </Button>
                                {playerData.methods.length > 0 && (
                                  <Button
                                    onClick={() => setEditingPlayerMethods(
                                      editingPlayerMethods === playerData.player_id ? null : playerData.player_id
                                    )}
                                    size="sm"
                                    variant="ghost"
                                    className="h-7 px-2 text-xs"
                                  >
                                    <Edit className="w-3 h-3 mr-1" />
                                    Edit
                                  </Button>
                                )}
                              </div>
                            </td>
                          </tr>
                          {editingPlayerMethods === playerData.player_id && (
                            <tr key={`${playerData.player_id}-edit`} className="bg-muted/20">
                              <td colSpan={3} className="px-4 py-3">
                                <div className="space-y-2">
                                  {playerData.methods.map((method) => (
                                    <div
                                      key={method.id}
                                      className="flex items-center justify-between p-2 rounded bg-background border border-border"
                                    >
                                      <div className="flex items-center gap-2">
                                        {method.is_primary && (
                                          <Star className="w-3 h-3 text-primary fill-primary flex-shrink-0" />
                                        )}
                                        <div className="text-xs">
                                          <span className="font-medium">{method.payment_method}:</span>{' '}
                                          <span className="text-muted-foreground">{method.payment_address}</span>
                                        </div>
                                      </div>
                                      <div className="flex items-center gap-1">
                                        {!method.is_primary && (
                                          <Button
                                            onClick={() => handleSetPrimary(playerData.player_id, method.id)}
                                            size="sm"
                                            variant="ghost"
                                            className="h-6 px-2 text-xs"
                                            disabled={submitLoading}
                                          >
                                            <Star className="w-3 h-3 mr-1" />
                                            Set Primary
                                          </Button>
                                        )}
                                        <Button
                                          onClick={() => handleEditMethod(playerData.player_id, method)}
                                          size="sm"
                                          variant="ghost"
                                          className="h-6 px-2 text-xs"
                                        >
                                          <Edit className="w-3 h-3 mr-1" />
                                          Edit
                                        </Button>
                                        <Button
                                          onClick={() => {
                                            setMethodPlayerId(playerData.player_id);
                                            setMethodToDelete(method);
                                          }}
                                          size="sm"
                                          variant="ghost"
                                          className="h-6 px-2 text-xs text-destructive hover:text-destructive"
                                          disabled={submitLoading}
                                        >
                                          <Trash2 className="w-3 h-3 mr-1" />
                                          Delete
                                        </Button>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </td>
                            </tr>
                          )}
                        </>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Mobile Compact List View */}
                <div className="md:hidden space-y-2">
                  {paymentMethods.map((playerData) => (
                    <div key={playerData.player_id} className="border border-border rounded p-2">
                      <div className="flex items-center justify-between mb-2">
                        <Text variant="bodySmall" weight="medium">{playerData.player_name}</Text>
                        <div className="flex items-center gap-1">
                          <Button
                            onClick={() => handleAddMethod(playerData.player_id)}
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2 text-xs"
                          >
                            <Plus className="w-3 h-3" />
                          </Button>
                          {playerData.methods.length > 0 && (
                            <Button
                              onClick={() => setEditingPlayerMethods(
                                editingPlayerMethods === playerData.player_id ? null : playerData.player_id
                              )}
                              size="sm"
                              variant="ghost"
                              className="h-7 px-2 text-xs"
                            >
                              <Edit className="w-3 h-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                      {playerData.methods.length > 0 ? (
                        <>
                          <div className="flex flex-wrap gap-1.5 mb-2">
                            {playerData.methods.map((method) => (
                              <div
                                key={method.id}
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${
                                  method.is_primary
                                    ? 'border-primary bg-primary/10 text-primary'
                                    : 'border-border bg-muted/50'
                                }`}
                              >
                                {method.is_primary && (
                                  <Star className="w-3 h-3 fill-primary text-primary" />
                                )}
                                <span className="font-medium">{method.payment_method}:</span>
                                <span className="text-muted-foreground">{method.payment_address}</span>
                              </div>
                            ))}
                          </div>
                          {editingPlayerMethods === playerData.player_id && (
                            <div className="space-y-1 pt-2 border-t border-border">
                              {playerData.methods.map((method) => (
                                <div
                                  key={method.id}
                                  className="flex items-center justify-between p-1.5 rounded bg-background border border-border"
                                >
                                  <div className="flex items-center gap-1.5 flex-1 min-w-0">
                                    {method.is_primary && (
                                      <Star className="w-3 h-3 text-primary fill-primary flex-shrink-0" />
                                    )}
                                    <div className="truncate text-xs">
                                      <span className="font-medium">{method.payment_method}:</span>{' '}
                                      <span className="text-muted-foreground">{method.payment_address}</span>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-0.5 ml-2 flex-shrink-0">
                                    {!method.is_primary && (
                                      <button
                                        onClick={() => handleSetPrimary(playerData.player_id, method.id)}
                                        className="p-1 text-muted-foreground hover:text-foreground"
                                        disabled={submitLoading}
                                        title="Set as primary"
                                      >
                                        <Star className="w-3 h-3" />
                                      </button>
                                    )}
                                    <button
                                      onClick={() => handleEditMethod(playerData.player_id, method)}
                                      className="p-1 text-muted-foreground hover:text-foreground"
                                      title="Edit"
                                    >
                                      <Edit className="w-3 h-3" />
                                    </button>
                                    <button
                                      onClick={() => {
                                        setMethodPlayerId(playerData.player_id);
                                        setMethodToDelete(method);
                                      }}
                                      className="p-1 text-muted-foreground hover:text-destructive"
                                      disabled={submitLoading}
                                      title="Delete"
                                    >
                                      <Trash2 className="w-3 h-3" />
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </>
                      ) : (
                        <Text variant="caption" color="muted">No methods added</Text>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center">
                <CreditCard className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <Text variant="body" color="muted">No payment methods configured yet</Text>
              </div>
            )}
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

              <form onSubmit={handleUpdatePayment} className="p-4 md:p-6 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                      {(paymentSummary || []).map((player) => (
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

                <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 pt-4">
                  <Button
                    type="button"
                    onClick={() => setEditingPayment(null)}
                    variant="outline"
                    className="w-full sm:w-auto min-h-[44px]"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={submitLoading}
                    className="bg-black text-white hover:opacity-90 w-full sm:w-auto min-h-[44px]"
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

        {/* Add/Edit Payment Method Modal */}
        {showMethodModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border max-w-md w-full mx-4">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <Heading variant="h3">{editingMethod ? 'Edit' : 'Add'} Payment Method</Heading>
                <Button
                  onClick={() => setShowMethodModal(false)}
                  variant="ghost"
                  size="icon-sm"
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-6 h-6" />
                </Button>
              </div>

              <form onSubmit={handleSaveMethod} className="p-6 space-y-4">
                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Payment Method *
                  </Text>
                  <select
                    value={methodForm.payment_method}
                    onChange={(e) => setMethodForm({...methodForm, payment_method: e.target.value})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    required
                  >
                    <option value="">Select method...</option>
                    <option value="Venmo">Venmo</option>
                    <option value="Zelle">Zelle</option>
                    <option value="Apple Cash">Apple Cash</option>
                    <option value="Cash">Cash</option>
                    <option value="PayPal">PayPal</option>
                    <option value="Bank Transfer">Bank Transfer</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div>
                  <Text variant="bodySmall" weight="medium" as="label" className="block mb-1">
                    Address/Handle *
                  </Text>
                  <input
                    type="text"
                    value={methodForm.payment_address}
                    onChange={(e) => setMethodForm({...methodForm, payment_address: e.target.value})}
                    className="w-full px-3 py-2 border border-input rounded-md focus:ring-ring focus:border-ring bg-background text-foreground"
                    placeholder="@username, phone, or email"
                    required
                  />
                  <Text variant="caption" color="muted" className="mt-1">
                    For Venmo, enter your username (@ will be added automatically)
                  </Text>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_primary"
                    checked={methodForm.is_primary}
                    onChange={(e) => setMethodForm({...methodForm, is_primary: e.target.checked})}
                    className="rounded border-input"
                  />
                  <Text variant="bodySmall" as="label" htmlFor="is_primary">
                    Set as primary payment method
                  </Text>
                </div>

                <div className="flex justify-end gap-3 pt-4">
                  <Button
                    type="button"
                    onClick={() => setShowMethodModal(false)}
                    variant="outline"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={submitLoading}
                    className="bg-black text-white hover:opacity-90"
                  >
                    {submitLoading ? 'Saving...' : 'Save'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Payment Method Confirmation Modal */}
        {methodToDelete && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border max-w-md w-full mx-4">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <Heading variant="h3">Confirm Delete</Heading>
                <Button
                  onClick={() => setMethodToDelete(null)}
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
                    <Text variant="bodyLarge" weight="medium" as="h4">Delete Payment Method</Text>
                    <Text variant="bodySmall" color="muted">This action cannot be undone.</Text>
                  </div>
                </div>

                <div className="bg-muted rounded-lg p-4 mb-4">
                  <Text variant="bodySmall" weight="medium" className="mb-1">
                    {methodToDelete.payment_method}
                  </Text>
                  <Text variant="caption" color="muted">
                    {methodToDelete.payment_address}
                  </Text>
                </div>

                <div className="flex justify-end space-x-3">
                  <Button
                    type="button"
                    onClick={() => setMethodToDelete(null)}
                    variant="outline"
                    disabled={submitLoading}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={confirmDeleteMethod}
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
                        Delete
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
