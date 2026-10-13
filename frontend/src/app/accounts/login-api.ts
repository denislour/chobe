import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterCredentials extends LoginCredentials {
  email: string;
  accept_terms: boolean;
}

export type RegistrationErrors = Partial<
  Record<keyof RegisterCredentials | 'non_field_errors', string[]>
>;

export interface LoginUser {
  id: number;
  username: string;
}

export interface SessionResponse {
  user: LoginUser | null;
}

export interface ResetPasswordCredentials {
  uid: string;
  token: string;
  password: string;
  password_confirm: string;
}

export type PasswordResetErrors = Partial<
  Record<'email' | keyof ResetPasswordCredentials | 'non_field_errors', string[]>
>;

@Injectable({ providedIn: 'root' })
export class LoginApi {
  constructor(private readonly http: HttpClient) {}

  session(): Observable<SessionResponse> {
    return this.http.get<SessionResponse>('/api/v1/auth/session/');
  }

  logout(): Observable<void> {
    return this.http.post<void>('/api/v1/auth/logout/', {});
  }

  login(credentials: LoginCredentials): Observable<LoginUser> {
    return this.http.post<LoginUser>('/api/v1/auth/login/', credentials);
  }

  register(credentials: RegisterCredentials): Observable<LoginUser> {
    return this.http.post<LoginUser>('/api/v1/auth/register/', credentials);
  }

  forgotPassword(email: string): Observable<void> {
    return this.http.post<void>('/api/v1/auth/forgot-password/', { email });
  }

  resetPassword(credentials: ResetPasswordCredentials): Observable<void> {
    return this.http.post<void>('/api/v1/auth/reset-password/', credentials);
  }
}
