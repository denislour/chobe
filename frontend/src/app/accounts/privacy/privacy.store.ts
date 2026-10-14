import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import {
  catchError,
  exhaustMap,
  filter,
  Observable,
  pipe,
  switchMap,
  tap,
  throwError,
} from 'rxjs';
import { PrivacyApi, PrivacyData } from './privacy-api';
import { FieldErrors } from '@app/accounts/account-errors';
import { accountError } from '@app/accounts/account-errors';

interface PrivacyState {
  privacy: PrivacyData | null;
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
    loading: false,
    pending: false,
    notice: '',
    error: '',
    fieldErrors: {},
  });
  readonly privacy = this.state.privacy;
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
        this.api.privacy().pipe(
          tapResponse({
            next: (privacy) => patchState(this.state, { privacy }),
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
                notice: 'Privacy settings saved.',
              }),
            error: (error: HttpErrorResponse) => this.restoreSavedSettings(error),
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
    return this.api.privacy().pipe(
      tap((privacy) => patchState(this.state, { privacy })),
      switchMap(() => throwError(() => error)),
    );
  }

  private startRequest(): void {
    patchState(this.state, { pending: true, notice: '', error: '', fieldErrors: {} });
  }
}
