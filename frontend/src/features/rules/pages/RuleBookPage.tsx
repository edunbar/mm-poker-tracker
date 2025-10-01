import { Plus, Edit, Trash2, Save, X } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useAdminSession } from '../../../contexts/AdminSessionContext';
import { useToast } from '../../../contexts/ToastContext';
import { Button } from '../../../shared/ui/button';
import { FormField, FormLabel } from '../../../shared/ui/form-field';
import { Input } from '../../../shared/ui/input';
import { Textarea } from '../../../shared/ui/textarea';
import { Heading, Text } from '../../../shared/ui/typography';
import { GameRule, getRules, createRule, updateRule, deleteRule } from '../api/rulesApi';

interface RuleBookPageProps {
  publicCode: string;
}

interface EditingRule {
  id?: string;
  title: string;
  content: string;
  isNew?: boolean;
}

export default function RuleBookPage({ publicCode }: RuleBookPageProps) {
  const { hasAdminSession, adminCode } = useAdminSession();
  const { showSuccess, showError } = useToast();
  const [rules, setRules] = useState<GameRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingRule, setEditingRule] = useState<EditingRule | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ruleToDelete, setRuleToDelete] = useState<GameRule | null>(null);

  const loadRules = useCallback(async () => {
    try {
      setLoading(true);
      const rulesData = await getRules(publicCode);
      setRules(rulesData);
    } catch (error) {
      showError('Error', 'Failed to load rules');
    } finally {
      setLoading(false);
    }
  }, [publicCode, showError]);

  // Load rules on component mount
  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleCreateRule = () => {
    setEditingRule({
      title: '',
      content: '',
      isNew: true
    });
  };

  const handleEditRule = (rule: GameRule) => {
    setEditingRule({
      id: rule.id,
      title: rule.title,
      content: rule.content,
      isNew: false
    });
  };

  const handleSaveRule = async () => {
    if (!editingRule || !adminCode) return;

    if (!editingRule.title.trim() || !editingRule.content.trim()) {
      showError('Error', 'Please fill in both title and content');
      return;
    }

    try {
      setIsSubmitting(true);

      if (editingRule.isNew) {
        const newRule = await createRule(publicCode, {
          title: editingRule.title.trim(),
          content: editingRule.content.trim()
        }, adminCode);

        setRules(prev => [...prev, newRule]);
        showSuccess('Success', 'Rule created successfully');
      } else if (editingRule.id) {
        const updatedRule = await updateRule(publicCode, editingRule.id, {
          title: editingRule.title.trim(),
          content: editingRule.content.trim()
        }, adminCode);

        setRules(prev => prev.map(rule =>
          rule.id === editingRule.id ? updatedRule : rule
        ));
        showSuccess('Success', 'Rule updated successfully');
      }

      setEditingRule(null);
    } catch (error) {
      showError('Error', 'Failed to save rule');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteRule = (rule: GameRule) => {
    setRuleToDelete(rule);
  };

  const confirmDeleteRule = async () => {
    if (!ruleToDelete || !adminCode) return;

    try {
      await deleteRule(publicCode, ruleToDelete.id, adminCode);
      setRules(prev => prev.filter(rule => rule.id !== ruleToDelete.id));
      setRuleToDelete(null);
      showSuccess('Success', 'Rule deleted successfully');
    } catch (error) {
      showError('Error', 'Failed to delete rule');
    }
  };

  const handleCancelEdit = () => {
    setEditingRule(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            <Text variant="body" color="muted" className="mt-2">Loading rules...</Text>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Heading variant="h1">Rule Book</Heading>
            <Text variant="body" color="muted" className="mt-1">Home game rules and guidelines</Text>
          </div>

          {hasAdminSession && (
            <Button
              onClick={handleCreateRule}
              className="flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Rule
            </Button>
          )}
        </div>

        {/* Rules List */}
        <div className="space-y-6">
          {rules.length === 0 ? (
            <div className="text-center py-12">
              <Text variant="body" color="muted">No rules have been added yet.</Text>
            </div>
          ) : (
            rules.map((rule, index) => (
              <div key={rule.id} className="bg-card rounded-lg border border-border p-6">
                {/* Rule Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 bg-primary/10 text-primary rounded-full font-semibold text-sm">
                      {index + 1}
                    </div>
                    <Heading variant="h2">{rule.title}</Heading>
                  </div>

                  {hasAdminSession && (
                    <div className="flex items-center gap-2">
                      <Button
                        onClick={() => handleEditRule(rule)}
                        variant="ghost"
                        size="icon-sm"
                        title="Edit rule"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        onClick={() => handleDeleteRule(rule)}
                        variant="ghost"
                        size="icon-sm"
                        className="hover:text-destructive"
                        title="Delete rule"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </div>

                {/* Rule Content */}
                <div className="prose prose-sm max-w-none text-foreground">
                  <div className="whitespace-pre-wrap">{rule.content}</div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Edit/Create Rule Modal */}
        {editingRule && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-card rounded-lg border border-border w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <Heading variant="h3">
                    {editingRule.isNew ? 'Add New Rule' : 'Edit Rule'}
                  </Heading>
                  <Button
                    onClick={handleCancelEdit}
                    variant="ghost"
                    size="icon-sm"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                <div className="space-y-4">
                  {/* Title Input */}
                  <FormField>
                    <FormLabel>
                      Rule Title
                    </FormLabel>
                    <Input
                      type="text"
                      value={editingRule.title}
                      onChange={(e) => setEditingRule(prev => prev ? { ...prev, title: e.target.value } : null)}
                      placeholder="Enter rule title..."
                    />
                  </FormField>

                  {/* Content Input */}
                  <FormField>
                    <FormLabel>
                      Rule Content
                    </FormLabel>
                    <Textarea
                      value={editingRule.content}
                      onChange={(e) => setEditingRule(prev => prev ? { ...prev, content: e.target.value } : null)}
                      rows={8}
                      placeholder="Enter rule content..."
                    />
                  </FormField>
                </div>

                {/* Modal Actions */}
                <div className="flex items-center justify-end gap-3 mt-6">
                  <Button
                    onClick={handleCancelEdit}
                    variant="outline"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSaveRule}
                    disabled={isSubmitting}
                    className="flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    {isSubmitting ? 'Saving...' : 'Save Rule'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {ruleToDelete && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-card rounded-lg border border-border w-full max-w-md">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <Heading variant="h3">Confirm Delete</Heading>
                  <Button
                    onClick={() => setRuleToDelete(null)}
                    variant="ghost"
                    size="icon-sm"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                <div className="mb-6">
                  <Text variant="body" color="muted" className="mb-4">
                    Are you sure you want to delete this rule? This action cannot be undone.
                  </Text>
                  <div className="bg-muted p-4 rounded-md">
                    <Text variant="body" weight="medium">{ruleToDelete.title}</Text>
                    <Text variant="bodySmall" color="muted" className="mt-1 line-clamp-3">
                      {ruleToDelete.content}
                    </Text>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3">
                  <Button
                    onClick={() => setRuleToDelete(null)}
                    variant="outline"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={confirmDeleteRule}
                    variant="destructive"
                  >
                    Delete Rule
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