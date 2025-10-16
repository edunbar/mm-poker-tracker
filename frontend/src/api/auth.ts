import type { LoginResponse, RegisterResponse, User } from '../types/auth';
import { apiClient } from './client';

export async function loginUser(
  email: string,
  password: string,
  rememberMe = false
): Promise<LoginResponse> {
  const response = await apiClient.post<any>('/api/auth/login', {
    email,
    password,
    remember_me: rememberMe,
  });
  // Transform snake_case to camelCase
  return {
    access_token: response.data.access_token,
    user: {
      id: response.data.user.id,
      email: response.data.user.email,
      displayName: response.data.user.display_name,
      emailVerified: response.data.user.email_verified,
      lastLoginAt: response.data.user.last_login_at,
    },
  };
}

export async function registerUser(
  email: string,
  password: string,
  displayName: string
): Promise<RegisterResponse> {
  const response = await apiClient.post<any>('/api/auth/register', {
    email,
    password,
    display_name: displayName,
  });
  // Transform snake_case to camelCase
  return {
    access_token: response.data.access_token,
    user: {
      id: response.data.user.id,
      email: response.data.user.email,
      displayName: response.data.user.display_name,
    },
  };
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<any>('/api/auth/me');
  // Transform snake_case to camelCase
  return {
    id: response.data.id,
    email: response.data.email,
    displayName: response.data.display_name,
    emailVerified: response.data.email_verified,
    createdAt: response.data.created_at,
    lastLoginAt: response.data.last_login_at,
  };
}

export async function updateUserProfile(displayName: string): Promise<User> {
  const response = await apiClient.patch<any>('/api/auth/profile', {
    display_name: displayName,
  });
  // Transform snake_case to camelCase
  return {
    id: response.data.user.id,
    email: response.data.user.email,
    displayName: response.data.user.display_name,
  };
}

export async function updatePassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiClient.patch('/api/auth/password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

export async function deleteAccount(password: string, confirmation: string): Promise<void> {
  await apiClient.delete('/api/auth/account', {
    data: {
      password,
      confirmation,
    },
  });
}
