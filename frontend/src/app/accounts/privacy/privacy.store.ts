import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import {
  catchError,
  exhaustMap,
  filter,
  forkJoin,
  Observable,
  pipe,
  switchMap,
  tap,
  throwError,
} from 'rxjs';
import { PrivacyApi, HistoryEntry, PrivacyData } from './privacy-api';
import { FieldErrors } from '@app/accounts/account-errors';
import { accountError } from '@app/accounts/account-errors';

interface PrivacyState {
  privacy: PrivacyData | null;
  history: HistoryEntry[];
  loading: boolean;
  pending: boolean;
  notice: string;
  error: string;
  fieldErrors: FieldErrors;
}

@Injectable()
export class PrivacyStore {
  private readonly state = signalState<PrivacyState>({
    privacy: null,
    history: [],
    loading: false,
    pending: false,
    notice: '',
    error: '',
    fieldErrors: {},
  });
  readonly privacy = this.state.privacy;
  readonly history = this.state.history;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly notice = this.state.notice;
  readonly error = this.state.error;
  readonly fieldErrors = this.state.fieldErrors;

  constructor(private readonly api: PrivacyApi) {}

  readonly load = rxMethod<void>(
    pipe(
      filter(() => !this.pending()),
      tap(() => patchState(this.state, { loading: true, error: '', notice: '', fieldErrors: {} })),
      switchMap(() =>
        forkJoin({ privacy: this.api.privacy(), history: this.api.history() }).pipe(
          tapResponse({
            next: (values) => patchState(this.state, values),
            error: (error: HttpErrorResponse) => patchState(this.state, accountError(error)),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        ),
      ),
    ),
  );

  readonly save = rxMethod<Pick<PrivacyData, 'share_phone' | 'record_history' | 'version'>>(
    pipe(
      filter(() => !this.pending() && !this.loading()),
      tap(() => this.startRequest()),
      exhaustMap((values) =>
        this.api.savePrivacy(values).pipe(
          catchError((error: HttpErrorResponse) => this.recoverConflict(error)),
          tapResponse({
            next: (privacy) =>
              patchState(this.state, {
                privacy,
                history: privacy.record_history ? this.history() : [],
                notice: 'Privacy settings saved.',
              }),
            error: (error: HttpErrorResponse) => this.restoreSavedSettings(error),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  readonly clearHistory = rxMethod<void>(
    pipe(
      filter(() => !this.pending()),
      tap(() => this.startRequest()),
      exhaustMap(() =>
        this.api.clearHistory().pipe(
          tapResponse({
            next: () =>
              patchState(this.state, { history: [], notice: 'Browsing history cleared.' }),
            error: (error: HttpErrorResponse) => patchState(this.state, accountError(error)),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  dismissNotification(): void {
    patchState(this.state, { error: '', notice: '' });
  }

  private restoreSavedSettings(error: HttpErrorResponse): void {
    const privacy = this.privacy();
    patchState(this.state, {
      ...accountError(error),
      privacy: privacy ? { ...privacy } : null,
    });
  }

  private recoverConflict(error: HttpErrorResponse): Observable<never> {
    if (error.status !== 409) return throwError(() => error);
    return forkJoin({ privacy: this.api.privacy(), history: this.api.history() }).pipe(
      tap((values) => patchState(this.state, values)),
      switchMap(() => throwError(() => error)),
    );
  }

  private startRequest(): void {
    patchState(this.state, { pending: true, notice: '', error: '', fieldErrors: {} });
  }
}
