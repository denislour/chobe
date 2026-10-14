import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, pipe, switchMap, tap } from 'rxjs';
import { ProfileApi, ProfileData } from './profile-api';
import { FieldErrors } from '@app/accounts/account-errors';
import { accountError } from '@app/accounts/account-errors';

interface ProfileState {
  profile: ProfileData | null;
  loading: boolean;
  pending: boolean;
  saved: boolean;
  error: string;
  fieldErrors: FieldErrors;
}

@Injectable()
export class ProfileStore {
  private readonly state = signalState<ProfileState>({
    profile: null,
    loading: false,
    pending: false,
    saved: false,
    error: '',
    fieldErrors: {},
  });
  readonly profile = this.state.profile;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly saved = this.state.saved;
  readonly error = this.state.error;
  readonly fieldErrors = this.state.fieldErrors;

  constructor(private readonly api: ProfileApi) {}

  readonly load = rxMethod<void>(
    pipe(
      filter(() => !this.pending()),
      tap(() =>
        patchState(this.state, { loading: true, saved: false, error: '', fieldErrors: {} }),
      ),
      switchMap(() =>
        this.api.profile().pipe(
          tapResponse({
            next: (profile) => patchState(this.state, { profile }),
            error: (error: HttpErrorResponse) => patchState(this.state, accountError(error)),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        ),
      ),
    ),
  );

  readonly save = rxMethod<FormData>(
    pipe(
      filter(() => !this.pending() && !this.loading()),
      tap(() =>
        patchState(this.state, { pending: true, saved: false, error: '', fieldErrors: {} }),
      ),
      exhaustMap((values) =>
        this.api.saveProfile(values).pipe(
          tapResponse({
            next: (profile) => patchState(this.state, { profile, saved: true }),
            error: (error: HttpErrorResponse) => patchState(this.state, accountError(error)),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );
}
