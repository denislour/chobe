import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { of, pipe, switchMap } from 'rxjs';
import { AttributeDefinition } from '@app/domain/category/category-types';
import { listingError } from '@app/shared/errors/listing-errors';
import { PublicListing } from '@app/listings/listing-types';
import { ComparisonApi } from '@app/data-access/discovery/comparison-api';
interface CompareState {
  listings: PublicListing[];
  unavailable: number[];
  loading: boolean;
  error: string;
}
@Injectable()
export class ComparisonPageStore {
  private readonly state = signalState<CompareState>({
    listings: [],
    unavailable: [],
    loading: false,
    error: '',
  });
  readonly listings = this.state.listings;
  readonly unavailable = this.state.unavailable;
  readonly loading = this.state.loading;
  readonly error = this.state.error;
  readonly fields = computed(() => {
    const fields = new Map<string, AttributeDefinition>();
    for (const item of this.listings())
      for (const field of item.category_schema.attributes) fields.set(field.key, field);
    return [...fields.values()];
  });
  constructor(private readonly api: ComparisonApi) {}
  readonly load = rxMethod<string>(
    pipe(
      switchMap((ids) => {
        patchState(this.state, { loading: true, error: '', listings: [], unavailable: [] });
        return (ids ? this.api.compare(ids) : of({ results: [], unavailable: [] })).pipe(
          tapResponse({
            next: (result) =>
              patchState(this.state, { listings: result.results, unavailable: result.unavailable }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );
}
