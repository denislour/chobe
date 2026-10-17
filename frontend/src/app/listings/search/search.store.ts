import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { pipe, switchMap } from 'rxjs';
import { listingError } from '@app/listings/listing-errors';
import { PublicListing, SearchFilters } from '@app/listings/listing-types';
import { DiscoveryApi } from './discovery-api';
interface SearchState {
  listings: PublicListing[];
  count: number;
  loading: boolean;
  error: string;
}
@Injectable()
export class SearchStore {
  private readonly state = signalState<SearchState>({
    listings: [],
    count: 0,
    loading: false,
    error: '',
  });
  readonly listings = this.state.listings;
  readonly count = this.state.count;
  readonly loading = this.state.loading;
  readonly error = this.state.error;
  constructor(private readonly api: DiscoveryApi) {}
  readonly load = rxMethod<SearchFilters>(
    pipe(
      switchMap((filters) => {
        patchState(this.state, { loading: true, error: '', listings: [], count: 0 });
        return this.api.list(filters).pipe(
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
}
