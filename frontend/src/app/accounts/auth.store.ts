import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, firstValueFrom, pipe, tap, timeout } from 'rxjs';
import {
  LoginApi,
  LoginCredentials,
  LoginUser,
  RegisterCredentials,
  RegistrationErrors,
} from './login-api';

interface AuthState {
  user: LoginUser | null;
  pending: boolean;
  error: string;
  sessionError: string;
  registrationErrors: RegistrationErrors;
}

const securityError = 'Your security check expired. Reload this page and try again.';
const loginErrors: Record<number, string> = {
  400: 'Invalid username or password.',
  403: securityError,
  429: 'Too many login attempts. Wait a minute and try again.',
};

@Injectable({ providedIn: 'root' })
export class AuthStore {
  private readonly state = signalState<AuthState>({
    user: null,
    pending: false,
    error: '',
    sessionError: '',
    registrationErrors: {},
  });

  readonly user = this.state.user;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly sessionError = this.state.sessionError;
  readonly registrationErrors = this.state.registrationErrors;

  constructor(private readonly api: LoginApi) {}

  readonly register = rxMethod<RegisterCredentials>(
    pipe(
      filter(() => !this.pending() && !this.user()),
      tap(() => this.startRequest()),
      exhaustMap((credentials) =>
        this.api.register(credentials).pipe(
          tapResponse({
            next: (user) => this.setUser(user),
            error: (error: HttpErrorResponse) => this.setRegistrationError(error),
            finalize: () => this.finishRequest(),
          }),
        ),
      ),
    ),
  );

  readonly login = rxMethod<LoginCredentials>(
    pipe(
      filter(() => !this.pending() && !this.user()),
      tap(() => this.startRequest()),
      exhaustMap((credentials) =>
        this.api.login(credentials).pipe(
          tapResponse({
            next: (user) => this.setUser(user),
            error: (error: HttpErrorResponse) => this.setLoginError(error),
            finalize: () => this.finishRequest(),
          }),
        ),
      ),
    ),
  );

  readonly logout = rxMethod<void>(
    pipe(
      filter(() => !this.pending()),
      tap(() => this.startRequest()),
      exhaustMap(() =>
        this.api.logout().pipe(
          tapResponse({
            next: () => this.setUser(null),
            error: (error: HttpErrorResponse) => this.setLogoutError(error),
            finalize: () => this.finishRequest(),
          }),
        ),
      ),
    ),
  );

  async restoreSession(): Promise<void> {
    if (this.pending()) return;
    this.startRequest();
    await firstValueFrom(
      this.api.session().pipe(
        timeout(5000),
        tapResponse({
          next: ({ user }) => this.setUser(user),
          error: () => this.setSessionError(),
          finalize: () => this.finishRequest(),
        }),
      ),
      { defaultValue: undefined },
    );
  }

  clearErrors(): void {
    patchState(this.state, { error: '', registrationErrors: {} });
  }

  private startRequest(): void {
    patchState(this.state, { pending: true, error: '', registrationErrors: {} });
  }

  private finishRequest(): void {
    patchState(this.state, { pending: false });
  }

  private setUser(user: LoginUser | null): void {
    patchState(this.state, { user, sessionError: '' });
  }

  private setLoginError(error: HttpErrorResponse): void {
    patchState(this.state, {
      error: loginErrors[error.status] ?? 'Unable to connect. Please try again.',
    });
  }

  private setLogoutError(error: HttpErrorResponse): void {
    patchState(this.state, {
      error: error.status === 403 ? securityError : 'Unable to log out. Please try again.',
    });
  }

  private setSessionError(): void {
    patchState(this.state, { sessionError: 'Unable to check your session. Please try again.' });
  }

  private setRegistrationError(error: HttpErrorResponse): void {
    const registrationErrors: RegistrationErrors = error.status === 400 ? (error.error ?? {}) : {};
    const messages: Record<number, string> = {
      400: registrationErrors.non_field_errors?.[0] ?? 'Check the highlighted fields.',
      403: securityError,
      429: 'Too many sign-up attempts. Wait a minute and try again.',
    };
    patchState(this.state, {
      registrationErrors,
      error: messages[error.status] ?? 'Unable to create your account. Please try again.',
    });
  }
}
