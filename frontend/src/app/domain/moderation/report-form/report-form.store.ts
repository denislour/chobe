import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, pipe, tap } from 'rxjs';
import { listingError } from '@app/shared/errors/listing-errors';
import { ReportsApi, ReportValues } from '@app/data-access/moderation/reports-api';
interface ReportFormState {
  pending: boolean;
  error: string;
  receipt: string;
}
@Injectable()
export class ReportFormStore {
  private readonly state = signalState<ReportFormState>({ pending: false, error: '', receipt: '' });
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly receipt = this.state.receipt;
  constructor(private readonly api: ReportsApi) {}
  readonly submit = rxMethod<ReportValues>(
    pipe(
      filter(() => !this.pending() && !this.receipt()),
      tap(() => patchState(this.state, { pending: true, error: '' })),
      exhaustMap((values) =>
        this.api.create(values).pipe(
          tapResponse({
            next: (report) => patchState(this.state, { receipt: report.id }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );
}
