import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, forkJoin, pipe, switchMap, tap } from 'rxjs';
import { listingError } from '@app/shared/errors/listing-errors';
import { ListingAudit, ModerationCase } from '@app/listings/listing-types';
import { ModerationApi } from './moderation-api';
interface ReviewFilters {
  status: string;
  appeals: boolean;
  page: number;
}
interface ModerationState {
  cases: ModerationCase[];
  count: number;
  selected: ModerationCase | null;
  history: ListingAudit[];
  loading: boolean;
  selecting: boolean;
  pending: boolean;
  error: string;
  notice: string;
}
@Injectable()
export class ModerationStore {
  private readonly state = signalState<ModerationState>({
    cases: [],
    count: 0,
    selected: null,
    history: [],
    loading: false,
    selecting: false,
    pending: false,
    error: '',
    notice: '',
  });
  private filters: ReviewFilters = { status: 'pending', appeals: false, page: 1 };
  readonly cases = this.state.cases;
  readonly count = this.state.count;
  readonly selected = this.state.selected;
  readonly history = this.state.history;
  readonly loading = this.state.loading;
  readonly selecting = this.state.selecting;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly notice = this.state.notice;
  constructor(private readonly api: ModerationApi) {}
  readonly load = rxMethod<ReviewFilters>(
    pipe(
      switchMap((filters) => {
        this.filters = filters;
        patchState(this.state, { loading: true, error: '' });
        return this.api.list(filters.status, filters.appeals, filters.page).pipe(
          tapResponse({
            next: (page) => patchState(this.state, { cases: page.results, count: page.count }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );
  readonly select = rxMethod<number>(
    pipe(
      filter(() => !this.pending()),
      switchMap((id) => {
        patchState(this.state, {
          selecting: true,
          selected: null,
          error: '',
          history: [],
          notice: '',
        });
        return forkJoin({ selected: this.api.retrieve(id), history: this.api.history(id) }).pipe(
          tapResponse({
            next: (data) => patchState(this.state, data),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { selecting: false }),
          }),
        );
      }),
    ),
  );
  readonly decide = rxMethod<{ decision: 'approve' | 'reject'; reason: string }>(
    pipe(
      filter(() => !this.pending() && !this.selecting() && !!this.selected()?.current),
      tap(() => patchState(this.state, { pending: true, error: '', notice: '' })),
      exhaustMap((values) => {
        const review = this.selected()!;
        return this.api.decision(review.id, review.version, values.decision, values.reason).pipe(
          tapResponse({
            next: (selected) => {
              patchState(this.state, {
                selected,
                notice:
                  values.decision === 'approve'
                    ? 'This snapshot is approved and published.'
                    : 'This snapshot was rejected. The seller can edit or appeal.',
              });
              this.load(this.filters);
            },
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        );
      }),
    ),
  );
}
