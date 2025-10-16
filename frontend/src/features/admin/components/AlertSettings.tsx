import axios from 'axios';
import { AlertTriangle, Edit2, Plus, Save, Trash2, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL } from '../../../config/api';
import { useAdminSession } from '../../../contexts/AdminSessionContext';

interface AlertRule {
  id: string;
  rule_type: 'amount_threshold' | 'days_overdue';
  threshold_value: number;
  is_active: boolean;
}

interface AlertSettingsProps {
  publicCode: string;
}

export function AlertSettings({ publicCode }: AlertSettingsProps) {
  const { getAdminCode } = useAdminSession();
  const adminCode = getAdminCode(publicCode);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [isAddingRule, setIsAddingRule] = useState(false);
  const [newRuleType, setNewRuleType] = useState<'amount_threshold' | 'days_overdue'>('amount_threshold');
  const [newThreshold, setNewThreshold] = useState('');
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
  const [editThreshold, setEditThreshold] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRules = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(
        `${API_BASE_URL}/api/games/${publicCode}/alerts/rules`,
        { headers: { 'X-Admin-Code': adminCode } }
      );
      setRules(response.data.rules);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } } };
      setError(error.response?.data?.error || 'Failed to fetch alert rules');
    } finally {
      setLoading(false);
    }
  }, [publicCode, getAdminCode]);

  useEffect(() => {
    if (publicCode) {
      fetchRules();
    }
  }, [publicCode, fetchRules]);

  const handleCreateRule = async () => {
    if (!newThreshold || parseFloat(newThreshold) <= 0) {
      setError('Threshold must be a positive number');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const threshold = newRuleType === 'amount_threshold'
        ? Math.round(parseFloat(newThreshold) * 100)  // Convert dollars to cents
        : parseInt(newThreshold);  // Days as-is

      await axios.post(
        `${API_BASE_URL}/api/games/${publicCode}/alerts/rules`,
        {
          rule_type: newRuleType,
          threshold_value: threshold
        },
        { headers: { 'X-Admin-Code': adminCode } }
      );

      await fetchRules();
      setIsAddingRule(false);
      setNewThreshold('');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } } };
      setError(error.response?.data?.error || 'Failed to create rule');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateRule = async (ruleId: string) => {
    if (!editThreshold || parseFloat(editThreshold) <= 0) {
      setError('Threshold must be a positive number');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const rule = rules.find(r => r.id === ruleId);
      if (!rule) return;

      const threshold = rule.rule_type === 'amount_threshold'
        ? Math.round(parseFloat(editThreshold) * 100)
        : parseInt(editThreshold);

      await axios.put(
        `${API_BASE_URL}/api/games/${publicCode}/alerts/rules/${ruleId}`,
        {
          threshold_value: threshold,
          is_active: rule.is_active
        },
        { headers: { 'X-Admin-Code': adminCode } }
      );

      await fetchRules();
      setEditingRuleId(null);
      setEditThreshold('');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } } };
      setError(error.response?.data?.error || 'Failed to update rule');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!window.confirm('Delete this alert rule? This action cannot be undone.')) return;

    try {
      setLoading(true);
      setError(null);
      await axios.delete(
        `${API_BASE_URL}/api/games/${publicCode}/alerts/rules/${ruleId}`,
        { headers: { 'X-Admin-Code': adminCode } }
      );
      await fetchRules();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } } };
      setError(error.response?.data?.error || 'Failed to delete rule');
    } finally {
      setLoading(false);
    }
  };

  const formatThreshold = (rule: AlertRule) => {
    if (rule.rule_type === 'amount_threshold') {
      return `$${(rule.threshold_value / 100).toFixed(2)}`;
    }
    return `${rule.threshold_value} ${rule.threshold_value === 1 ? 'day' : 'days'}`;
  };

  const getRuleTypeLabel = (ruleType: string) => {
    return ruleType === 'amount_threshold' ? 'Amount Threshold' : 'Days Overdue';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-yellow-600" />
        <h3 className="text-lg font-semibold">Payment Alert Rules</h3>
      </div>

      <p className="text-sm text-muted-foreground">
        Configure alert rules to notify when players exceed payment thresholds or have overdue balances.
      </p>

      {error && (
        <div className="bg-destructive/10 border border-destructive rounded-lg p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Existing Rules */}
      <div className="space-y-2">
        {rules.length === 0 && !loading && (
          <div className="text-sm text-muted-foreground text-center py-6 border border-dashed rounded-lg">
            No alert rules configured. Create your first rule to get started.
          </div>
        )}

        {rules.map(rule => (
          <div
            key={rule.id}
            className="border rounded-lg p-4 flex justify-between items-center hover:bg-accent/50 transition-colors"
          >
            {editingRuleId === rule.id ? (
              <div className="flex items-center gap-2 flex-1">
                <input
                  type="number"
                  value={editThreshold}
                  onChange={(e) => setEditThreshold(e.target.value)}
                  className="border border-input bg-background px-3 py-2 rounded-md text-sm w-32"
                  placeholder={rule.rule_type === 'amount_threshold' ? 'Dollars' : 'Days'}
                  min="0"
                  step={rule.rule_type === 'amount_threshold' ? '0.01' : '1'}
                  disabled={loading}
                />
                <button
                  onClick={() => handleUpdateRule(rule.id)}
                  disabled={loading}
                  className="bg-primary text-primary-foreground px-3 py-2 rounded-md text-sm hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1"
                >
                  <Save className="w-4 h-4" />
                  Save
                </button>
                <button
                  onClick={() => {
                    setEditingRuleId(null);
                    setEditThreshold('');
                  }}
                  disabled={loading}
                  className="border border-input px-3 py-2 rounded-md text-sm hover:bg-accent disabled:opacity-50 flex items-center gap-1"
                >
                  <X className="w-4 h-4" />
                  Cancel
                </button>
              </div>
            ) : (
              <>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{getRuleTypeLabel(rule.rule_type)}</span>
                    {!rule.is_active && (
                      <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded">
                        Inactive
                      </span>
                    )}
                  </div>
                  <span className="text-sm text-muted-foreground">{formatThreshold(rule)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setEditingRuleId(rule.id);
                      setEditThreshold(
                        rule.rule_type === 'amount_threshold'
                          ? (rule.threshold_value / 100).toString()
                          : rule.threshold_value.toString()
                      );
                    }}
                    disabled={loading}
                    className="text-blue-600 hover:text-blue-700 disabled:opacity-50 flex items-center gap-1 text-sm"
                  >
                    <Edit2 className="w-4 h-4" />
                    Edit
                  </button>
                  <button
                    onClick={() => handleDeleteRule(rule.id)}
                    disabled={loading}
                    className="text-red-600 hover:text-red-700 disabled:opacity-50 flex items-center gap-1 text-sm"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Add New Rule Form */}
      {isAddingRule ? (
        <div className="border rounded-lg p-4 space-y-3 bg-accent/20">
          <div>
            <label className="block text-sm font-medium mb-1">Rule Type</label>
            <select
              value={newRuleType}
              onChange={(e) => setNewRuleType(e.target.value as 'amount_threshold' | 'days_overdue')}
              className="border border-input bg-background px-3 py-2 rounded-md text-sm w-full"
              disabled={loading}
            >
              <option value="amount_threshold">Amount Threshold</option>
              <option value="days_overdue">Days Overdue</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Threshold {newRuleType === 'amount_threshold' ? '(Dollars)' : '(Days)'}
            </label>
            <input
              type="number"
              value={newThreshold}
              onChange={(e) => setNewThreshold(e.target.value)}
              placeholder={newRuleType === 'amount_threshold' ? 'e.g., 50.00' : 'e.g., 14'}
              className="border border-input bg-background px-3 py-2 rounded-md text-sm w-full"
              min="0"
              step={newRuleType === 'amount_threshold' ? '0.01' : '1'}
              disabled={loading}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreateRule}
              disabled={loading || !newThreshold}
              className="bg-green-600 text-white px-4 py-2 rounded-md text-sm hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <Plus className="w-4 h-4" />
              Create Rule
            </button>
            <button
              onClick={() => {
                setIsAddingRule(false);
                setNewThreshold('');
              }}
              disabled={loading}
              className="border border-input px-4 py-2 rounded-md text-sm hover:bg-accent disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setIsAddingRule(true)}
          disabled={loading}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1"
        >
          <Plus className="w-4 h-4" />
          Add Alert Rule
        </button>
      )}
    </div>
  );
}
