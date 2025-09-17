import { API_BASE_URL } from '../config/api';

export interface BugReportData {
  description: string;
  steps_to_reproduce: string;
  category: string;
  user_email: string;
  url: string;
  user_agent: string;
  game_code?: string | undefined;
}

export interface BugReportResponse {
  success: boolean;
  message?: string;
  error?: string;
  details?: string | string[];
}

export interface BugCategoriesResponse {
  success: boolean;
  categories: string[];
}

export interface BugReportHealthResponse {
  success: boolean;
  email_configured: boolean;
  message: string;
}

/**
 * Submit a bug report
 */
export async function submitBugReport(data: BugReportData): Promise<BugReportResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/bug-report`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || `HTTP error! status: ${response.status}`);
    }

    return result;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error submitting bug report:', error);
    throw error;
  }
}

/**
 * Get available bug report categories
 */
export async function getBugCategories(): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/bug-report/categories`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: BugCategoriesResponse = await response.json();

    if (!result.success) {
      throw new Error('Failed to fetch bug categories');
    }

    return result.categories;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching bug categories:', error);
    // Return default categories if API fails
    return ['UI Issue', 'Functionality', 'Performance', 'Data Accuracy', 'Other'];
  }
}

/**
 * Check bug report service health
 */
export async function checkBugReportHealth(): Promise<BugReportHealthResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/bug-report/health`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error checking bug report health:', error);
    return {
      success: false,
      email_configured: false,
      message: 'Bug report service unavailable'
    };
  }
}