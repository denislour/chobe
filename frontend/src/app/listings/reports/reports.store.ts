import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, pipe, switchMap, tap } from 'rxjs';
import { listingError } from '@app/shared/errors/listing-errors';
import { ReportAudit, ReportDecisionValues, ReportRecord, ReportsApi } from '@app/data-access/moderation/reports-api';
interface ReportFilters {
  admin: boolean;
  page: number;
  status: string;
}
interface ReportsState {
  reports: ReportRecord[];
  count: number;
  selected: ReportRecord | null;
  history: ReportAudit[];
  loading: boolean;
  pending: boolean;
  error: string;
  notice: string;
}
@Injectable()
export class ReportsStore {
  private readonly state = signalState<ReportsState>({
    reports: [],
    count: 0,
    selected: null,
    history: [],
    loading: false,
    pending: false,
    error: '',
    notice: '',
  });
  private filters: ReportFilters = { admin: false, page: 1, status: '' };
  readonly reports = this.state.reports;
  readonly count = this.state.count;
  readonly selected = this.state.selected;
  readonly history = this.state.history;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly notice = this.state.notice;
  constructor(private readonly api: ReportsApi) {}
  readonly load = rxMethod<ReportFilters>(
    pipe(
      switchMap((filters) => {
        this.filters = filters;
        patchState(this.state, { loading: true, error: '' });
        return this.api.list(filters.admin, filters.page, filters.status).pipe(
          tapResponse({
            next: (page) => {
              const selected = this.selected();
              patchState(this.state, {
                reports: page.results,
                count: page.count,
                selected: selected
                  ? (page.results.find((report) => report.id === selected.id) ?? null)
                  : null,
              });
            },
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );
  readonly historyFor = rxMethod<string>(
    pipe(
      switchMap((id) =>
        this.api.history(id).pipe(
          tapResponse({
            next: (history) => patchState(this.state, { history }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
          }),
        ),
      ),
    ),
  );
  readonly decide = rxMethod<{ id: string; values: ReportDecisionValues }>(
    pipe(
      filter(() => !this.pending()),
      tap(() => patchState(this.state, { pending: true, error: '', notice: '' })),
      exhaustMap((value) =>
        this.api.decision(value.id, value.values).pipe(
          tapResponse({
            next: (selected) => {
              patchState(this.state, { selected, notice: 'Decision recorded.' });
              this.historyFor(selected.id);
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
  select(report: ReportRecord, admin: boolean): void {
    patchState(this.state, { selected: report, history: [], notice: '' });
    if (admin) this.historyFor(report.id);
  }
}
