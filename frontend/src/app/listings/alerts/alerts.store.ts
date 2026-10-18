import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { Observable, exhaustMap, filter, forkJoin, pipe, switchMap, tap } from 'rxjs';
import { listingError } from '@app/shared/errors/listing-errors';
import {
  AlertsApi,
  NotificationItem,
  NotificationPreferences,
  SavedSearch,
  SavedSearchValues,
} from './alerts-api';
interface AlertsState {
  searches: SavedSearch[];
  notifications: NotificationItem[];
  count: number;
  preferences: NotificationPreferences | null;
  loading: boolean;
  pending: boolean;
  error: string;
  notice: string;
}
type AlertAction =
  | { kind: 'save'; id: number | null; values: SavedSearchValues }
  | { kind: 'delete'; id: number }
  | { kind: 'read'; id: number }
  | { kind: 'readAll' }
  | { kind: 'preferences'; values: NotificationPreferences };
@Injectable()
export class AlertsStore {
  private readonly state = signalState<AlertsState>({
    searches: [],
    notifications: [],
    count: 0,
    preferences: null,
    loading: false,
    pending: false,
    error: '',
    notice: '',
  });
  private page = 1;
  readonly searches = this.state.searches;
  readonly notifications = this.state.notifications;
  readonly count = this.state.count;
  readonly preferences = this.state.preferences;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly notice = this.state.notice;
  constructor(private readonly api: AlertsApi) {}
  readonly load = rxMethod<number>(
    pipe(
      switchMap((page) => {
        this.page = page;
        patchState(this.state, { loading: true, error: '' });
        return forkJoin({
          searches: this.api.searches(),
          notifications: this.api.notifications(page),
          preferences: this.api.preferences(),
        }).pipe(
          tapResponse({
            next: (data) =>
              patchState(this.state, {
                searches: data.searches.results,
                notifications: data.notifications.results,
                count: data.notifications.count,
                preferences: data.preferences,
              }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );
  readonly change = rxMethod<AlertAction>(
    pipe(
      filter(() => !this.pending()),
      tap(() => patchState(this.state, { pending: true, error: '', notice: '' })),
      exhaustMap((action) =>
        this.request(action).pipe(
          tapResponse({
            next: () => {
              patchState(this.state, {
                notice:
                  action.kind === 'save'
                    ? 'Search saved. Manage its alerts in notification settings.'
                    : 'Your notification settings have been updated.',
              });
              if (action.kind !== 'save' || this.preferences()) this.load(this.page);
            },
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );
  save(value: { id: number | null; values: SavedSearchValues }): void {
    this.change({ kind: 'save', ...value });
  }
  private request(action: AlertAction): Observable<unknown> {
    switch (action.kind) {
      case 'save':
        return this.api.save(action.id, action.values);
      case 'delete':
        return this.api.remove(action.id);
      case 'read':
        return this.api.read(action.id);
      case 'readAll':
        return this.api.readAll();
      case 'preferences':
        return this.api.savePreferences(action.values);
    }
  }
}
