import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginUser {
  id: number;
  username: string;
}

export interface SessionResponse {
  user: LoginUser | null;
}

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
}
