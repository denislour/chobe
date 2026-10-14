import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, pipe, switchMap, take, takeWhile, tap, timer } from 'rxjs';
import { PrivacyApi, DeletionJob } from './privacy-api';
import { accountError } from '@app/accounts/account-errors';

interface DeletionReceiptState {
  job: DeletionJob | null;
  loading: boolean;
  error: string;
}

@Injectable()
export class DeletionReceiptStore {
  private readonly state = signalState<DeletionReceiptState>({
    job: null,
    loading: false,
    error: '',
  });
  readonly job = this.state.job;
  readonly loading = this.state.loading;
  readonly error = this.state.error;

  constructor(private readonly api: PrivacyApi) {}

  readonly load = rxMethod<string>(
    pipe(
      tap(() => patchState(this.state, { loading: true, error: '' })),
      switchMap((receipt) =>
        timer(0, 2000).pipe(
          take(15),
          exhaustMap(() => this.api.deletionStatus(receipt)),
          takeWhile((job) => job.status === 'requested' || job.status === 'processing', true),
          tapResponse({
            next: (job) => patchState(this.state, { job, loading: false }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: accountError(error).error }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        ),
      ),
    ),
  );
}
