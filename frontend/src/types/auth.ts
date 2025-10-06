export interface User {
  id: string;
  email: string;
  displayName: string;
  emailVerified?: boolean;
  createdAt?: string;
  lastLoginAt?: string;
}

export interface LoginResponse {
  access_token: string;
  user: User;
}

export interface RegisterResponse {
  access_token: string;
  user: User;
}

export interface AuthError {
  message: string;
  status?: number;
}
