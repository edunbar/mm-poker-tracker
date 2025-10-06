import type { LoginResponse, RegisterResponse, User } from '../types/auth';
import { apiClient } from './client';

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/api/auth/login', {
    email,
    password,
  });
  return response.data;
}

export async function registerUser(
  email: string,
  password: string,
  displayName: string
): Promise<RegisterResponse> {
  const response = await apiClient.post<RegisterResponse>('/api/auth/register', {
    email,
    password,
    display_name: displayName,
  });
  return response.data;
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/api/auth/me');
  return response.data;
}
