import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { pipe, switchMap } from 'rxjs';
import { CategoryApi } from '@app/data-access/categories/category-api';
import { CategoryData } from '@app/domain/category/category-types';
import { listingError } from '@app/shared/errors/listing-errors';
import { PublicListing } from '@app/domain/listing/listing-types';
import { DiscoveryApi } from '@app/data-access/discovery/discovery-api';
interface HomeState {
  categories: CategoryData[];
  listings: PublicListing[];
  categoriesLoading: boolean;
  listingsLoading: boolean;
  categoriesError: string;
  listingsError: string;
}
@Injectable()
export class HomeStore {
  private readonly state = signalState<HomeState>({
    categories: [],
    listings: [],
    categoriesLoading: false,
    listingsLoading: false,
    categoriesError: '',
    listingsError: '',
  });
  readonly categories = this.state.categories;
  readonly listings = this.state.listings;
  readonly categoriesLoading = this.state.categoriesLoading;
  readonly listingsLoading = this.state.listingsLoading;
  readonly categoriesError = this.state.categoriesError;
  readonly listingsError = this.state.listingsError;
  constructor(
    private readonly categoriesApi: CategoryApi,
    private readonly discovery: DiscoveryApi,
  ) {}
  readonly loadCategories = rxMethod<void>(
    pipe(
      switchMap(() => {
        patchState(this.state, { categoriesLoading: true, categoriesError: '' });
        return this.categoriesApi.list().pipe(
          tapResponse({
            next: (categories) => patchState(this.state, { categories }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { categoriesError: listingError(error) }),
            finalize: () => patchState(this.state, { categoriesLoading: false }),
          }),
        );
      }),
    ),
  );
  readonly loadListings = rxMethod<void>(
    pipe(
      switchMap(() => {
        patchState(this.state, { listingsLoading: true, listingsError: '' });
        return this.discovery.list({}).pipe(
          tapResponse({
            next: (page) => patchState(this.state, { listings: page.results }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { listingsError: listingError(error) }),
            finalize: () => patchState(this.state, { listingsLoading: false }),
          }),
        );
      }),
    ),
  );
}
