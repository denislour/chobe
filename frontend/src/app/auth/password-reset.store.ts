import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, pipe, tap } from 'rxjs';
import { AuthStore } from './auth.store';
import { AuthApi, PasswordResetErrors, ResetPasswordCredentials } from './auth-api';

interface PasswordResetState {
  pending: boolean;
  completed: boolean;
  error: string;
  fieldErrors: PasswordResetErrors;
}

@Injectable()
export class PasswordResetStore {
  private readonly state = signalState<PasswordResetState>({
    pending: false,
    completed: false,
    error: '',
    fieldErrors: {},
  });

  readonly pending = this.state.pending;
  readonly completed = this.state.completed;
  readonly error = this.state.error;
  readonly fieldErrors = this.state.fieldErrors;

  constructor(
    private readonly api: AuthApi,
    private readonly auth: AuthStore,
  ) {}

  readonly forgotPassword = rxMethod<string>(
    pipe(
      filter(() => !this.pending()),
      tap(() => this.startRequest()),
      exhaustMap((email) =>
        this.api.forgotPassword(email).pipe(
          tapResponse({
            next: () => patchState(this.state, { completed: true }),
            error: (error: HttpErrorResponse) => this.setError(error),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  readonly resetPassword = rxMethod<ResetPasswordCredentials>(
    pipe(
      filter(() => !this.pending()),
      tap(() => this.startRequest()),
      exhaustMap((credentials) =>
        this.api.resetPassword(credentials).pipe(
          tapResponse({
            next: () => this.finishReset(),
            error: (error: HttpErrorResponse) => this.setError(error),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  private finishReset(): void {
    this.auth.clearSession();
    patchState(this.state, { completed: true });
  }

  private startRequest(): void {
    patchState(this.state, { pending: true, completed: false, error: '', fieldErrors: {} });
  }

  private setError(error: HttpErrorResponse): void {
    const fieldErrors: PasswordResetErrors = error.status === 400 ? (error.error ?? {}) : {};
    const messages: Record<number, string> = {
      400: fieldErrors.non_field_errors?.[0] ?? 'Check the highlighted fields.',
      403: 'Your security check expired. Reload this page and try again.',
      429: 'Too many attempts. Please try again later.',
    };
    patchState(this.state, {
      fieldErrors,
      error: messages[error.status] ?? 'Unable to connect. Please try again.',
    });
  }
}
