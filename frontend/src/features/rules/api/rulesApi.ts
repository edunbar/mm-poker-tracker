import { API_BASE_URL } from '../../../config/api';

export interface GameRule {
  id: string;
  title: string;
  content: string;
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface CreateRuleData {
  title: string;
  content: string;
  order_index?: number;
}

export interface UpdateRuleData {
  title?: string;
  content?: string;
  order_index?: number;
}

export interface RuleReorderData {
  id: string;
  order_index: number;
}

/**
 * Fetch all rules for a game
 */
export async function getRules(publicCode: string): Promise<GameRule[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/games/${publicCode}/rules`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'Failed to fetch rules');
    }

    return result.rules;
  } catch (error) {
    console.error('Error fetching rules:', error);
    throw error;
  }
}

/**
 * Create a new rule (admin only)
 */
export async function createRule(
  publicCode: string,
  ruleData: CreateRuleData,
  adminCode: string
): Promise<GameRule> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/games/${publicCode}/rules`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Code': adminCode,
      },
      body: JSON.stringify(ruleData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'Failed to create rule');
    }

    return result.rule;
  } catch (error) {
    console.error('Error creating rule:', error);
    throw error;
  }
}

/**
 * Update an existing rule (admin only)
 */
export async function updateRule(
  publicCode: string,
  ruleId: string,
  ruleData: UpdateRuleData,
  adminCode: string
): Promise<GameRule> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/games/${publicCode}/rules/${ruleId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Code': adminCode,
      },
      body: JSON.stringify(ruleData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'Failed to update rule');
    }

    return result.rule;
  } catch (error) {
    console.error('Error updating rule:', error);
    throw error;
  }
}

/**
 * Delete a rule (admin only)
 */
export async function deleteRule(
  publicCode: string,
  ruleId: string,
  adminCode: string
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/games/${publicCode}/rules/${ruleId}`, {
      method: 'DELETE',
      headers: {
        'X-Admin-Code': adminCode,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'Failed to delete rule');
    }
  } catch (error) {
    console.error('Error deleting rule:', error);
    throw error;
  }
}

/**
 * Reorder rules (admin only)
 */
export async function reorderRules(
  publicCode: string,
  ruleOrders: RuleReorderData[],
  adminCode: string
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/games/${publicCode}/rules/reorder`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Code': adminCode,
      },
      body: JSON.stringify({ rule_orders: ruleOrders }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'Failed to reorder rules');
    }
  } catch (error) {
    console.error('Error reordering rules:', error);
    throw error;
  }
}