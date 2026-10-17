import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { Observable, exhaustMap, filter, forkJoin, pipe, switchMap, tap } from 'rxjs';
import { listingError } from '@app/listings/listing-errors';
import { ListingDraft } from '@app/listings/listing-types';
import { ListingManagementApi, OwnerFilters } from './listing-management-api';
interface DashboardState {
  listings: ListingDraft[];
  summary: Partial<Record<string, number>>;
  count: number;
  loading: boolean;
  pending: boolean;
  error: string;
  notice: string;
}
export interface OwnerAction {
  listing: ListingDraft;
  kind: 'renew' | 'delete' | 'status';
  status?: string;
}
@Injectable()
export class DashboardStore {
  private readonly state = signalState<DashboardState>({
    listings: [],
    summary: {},
    count: 0,
    loading: false,
    pending: false,
    error: '',
    notice: '',
  });
  private filters: OwnerFilters = { state: '', q: '', page: 1, retention: '' };
  readonly listings = this.state.listings;
  readonly summary = this.state.summary;
  readonly count = this.state.count;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly notice = this.state.notice;
  constructor(private readonly api: ListingManagementApi) {}
  readonly load = rxMethod<OwnerFilters>(
    pipe(
      switchMap((filters) => {
        this.filters = filters;
        patchState(this.state, { loading: true, error: '' });
        return forkJoin({ page: this.api.list(filters), summary: this.api.summary() }).pipe(
          tapResponse({
            next: ({ page, summary }) =>
              patchState(this.state, { listings: page.results, count: page.count, summary }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );
  readonly change = rxMethod<OwnerAction>(
    pipe(
      filter(() => !this.pending() && !this.loading()),
      tap(() => patchState(this.state, { pending: true, error: '', notice: '' })),
      exhaustMap((action) =>
        this.request(action).pipe(
          tapResponse({
            next: () => {
              patchState(this.state, {
                notice:
                  action.kind === 'delete' ? 'Listing and photos deleted.' : 'Listing updated.',
              });
              this.load(this.filters);
            },
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );
  private request(action: OwnerAction): Observable<unknown> {
    const { id, version } = action.listing;
    switch (action.kind) {
      case 'renew':
        return this.api.renew(id, version);
      case 'delete':
        return this.api.remove(id, version);
      case 'status':
        return this.api.status(id, version, action.status ?? 'hidden');
    }
  }
}
