import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, map, pipe, switchMap, tap } from 'rxjs';
import { listingError } from '@app/shared/errors/listing-errors';
import { PublicListing } from '@app/listings/listing-types';
import { LibraryApi } from './library-api';
interface LibraryState {
  listings: PublicListing[];
  count: number;
  loading: boolean;
  pending: boolean;
  error: string;
  notice: string;
}
@Injectable()
export class LibraryStore {
  private readonly state = signalState<LibraryState>({
    listings: [],
    count: 0,
    loading: false,
    pending: false,
    error: '',
    notice: '',
  });
  readonly listings = this.state.listings;
  readonly count = this.state.count;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly notice = this.state.notice;
  constructor(private readonly api: LibraryApi) {}
  readonly load = rxMethod<{ mode: 'favorites' | 'history'; page: number }>(
    pipe(
      switchMap((value) => {
        patchState(this.state, { loading: true, error: '', listings: [], count: 0 });
        const request =
          value.mode === 'favorites'
            ? this.api.favorites(value.page)
            : this.api.history().pipe(map((results) => ({ results, count: results.length })));
        return request.pipe(
          tapResponse({
            next: (page) => patchState(this.state, { listings: page.results, count: page.count }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );
  readonly clear = rxMethod<void>(
    pipe(
      filter(() => !this.pending()),
      tap(() => patchState(this.state, { pending: true, error: '' })),
      exhaustMap(() =>
        this.api.clearHistory().pipe(
          tapResponse({
            next: () =>
              patchState(this.state, {
                listings: [],
                count: 0,
                notice: 'Your viewing history has been cleared.',
              }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );
}
