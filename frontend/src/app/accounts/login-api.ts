import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { switchMap } from 'rxjs';

export interface LoginUser {
  id: number;
  username: string;
}

@Injectable({ providedIn: 'root' })
export class LoginApi {
  private readonly http = inject(HttpClient);

  login(credentials: { username: string; password: string }) {
    return this.http
      .get<void>('/api/v1/auth/csrf/')
      .pipe(switchMap(() => this.http.post<LoginUser>('/api/v1/auth/login/', credentials)));
  }
}
