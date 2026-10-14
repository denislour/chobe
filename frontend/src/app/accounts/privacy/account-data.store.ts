import { HttpErrorResponse } from '@angular/common/http';
import { computed, Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, pipe, switchMap, take, takeWhile, tap, timer } from 'rxjs';
import { PrivacyApi, DeletionCredentials, AccountDataExportJob } from './privacy-api';
import { FieldErrors } from '@app/accounts/account-errors';
import { accountError } from '@app/accounts/account-errors';
import { AuthStore } from '@app/auth/auth.store';

interface AccountDataState {
  jobs: AccountDataExportJob[];
  loading: boolean;
  pending: boolean;
  deleting: boolean;
  receipt: string | null;
  error: string;
  fieldErrors: FieldErrors;
}

@Injectable()
export class AccountDataStore {
  private readonly state = signalState<AccountDataState>({
    jobs: [],
    loading: false,
    pending: false,
    deleting: false,
    receipt: null,
    error: '',
    fieldErrors: {},
  });
  readonly jobs = this.state.jobs;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly deleting = this.state.deleting;
  readonly receipt = this.state.receipt;
  readonly error = this.state.error;
  readonly fieldErrors = this.state.fieldErrors;
  readonly activeExport = computed(() =>
    this.jobs().some((job) => job.status === 'queued' || job.status === 'processing'),
  );

  constructor(
    private readonly api: PrivacyApi,
    private readonly auth: AuthStore,
  ) {}

  readonly load = rxMethod<void>(
    pipe(
      tap(() => patchState(this.state, { loading: true, error: '', fieldErrors: {} })),
      switchMap(() =>
        timer(0, 2000).pipe(
          take(15),
          exhaustMap(() => this.api.accountDataExports()),
          takeWhile(
            (jobs) => jobs.some((job) => job.status === 'queued' || job.status === 'processing'),
            true,
          ),
          tapResponse({
            next: (jobs) => patchState(this.state, { jobs, loading: false }),
            error: (error: HttpErrorResponse) => patchState(this.state, accountError(error)),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        ),
      ),
    ),
  );

  readonly createExport = rxMethod<void>(
    pipe(
      filter(() => !this.pending() && !this.deleting() && !this.activeExport()),
      tap(() => patchState(this.state, { pending: true, error: '', fieldErrors: {} })),
      exhaustMap(() =>
        this.api.createAccountDataExport().pipe(
          tapResponse({
            next: (job) => this.setExport(job),
            error: (error: HttpErrorResponse) =>
              patchState(
                this.state,
                accountError(error, 'You have reached the limit of 2 account exports per hour.'),
              ),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  readonly deleteAccount = rxMethod<DeletionCredentials>(
    pipe(
      filter(() => !this.deleting() && !this.pending()),
      tap(() => patchState(this.state, { deleting: true, error: '', fieldErrors: {} })),
      exhaustMap((values) =>
        this.api.deleteAccount(values).pipe(
          tapResponse({
            next: ({ receipt }) => this.finishDeletion(receipt),
            error: (error: HttpErrorResponse) => patchState(this.state, accountError(error)),
            finalize: () => patchState(this.state, { deleting: false }),
          }),
        ),
      ),
    ),
  );

  dismissNotification(): void {
    patchState(this.state, { error: '' });
  }

  private setExport(job: AccountDataExportJob): void {
    patchState(this.state, {
      jobs: [job, ...this.jobs().filter((entry) => entry.job_id !== job.job_id)],
    });
    this.load();
  }

  private finishDeletion(receipt: string): void {
    patchState(this.state, { receipt, jobs: [] });
    this.auth.clearSession();
  }
}
