import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, pipe, switchMap, tap } from 'rxjs';
import { LibraryApi } from '@app/data-access/engagement/library-api';
import { listingError } from '@app/shared/errors/listing-errors';
import { PublicListing } from '@app/listings/listing-types';
import { DiscoveryApi } from '@app/data-access/discovery/discovery-api';
interface DetailState {
  listing: PublicListing | null;
  loading: boolean;
  pending: boolean;
  error: string;
  actionError: string;
  notice: string;
  historyError: string;
}
@Injectable()
export class DetailStore {
  private readonly state = signalState<DetailState>({
    listing: null,
    loading: false,
    pending: false,
    error: '',
    actionError: '',
    notice: '',
    historyError: '',
  });
  readonly listing = this.state.listing;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly actionError = this.state.actionError;
  readonly notice = this.state.notice;
  readonly historyError = this.state.historyError;
  constructor(
    private readonly api: DiscoveryApi,
    private readonly library: LibraryApi,
  ) {}
  readonly load = rxMethod<{ id: number; record: boolean }>(
    pipe(
      switchMap((value) => {
        patchState(this.state, {
          listing: null,
          loading: true,
          error: '',
          actionError: '',
          notice: '',
          historyError: '',
        });
        return this.api.retrieve(value.id).pipe(
          tapResponse({
            next: (listing) => {
              patchState(this.state, { listing });
              if (value.record) this.recordHistory(listing.id);
            },
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );
  readonly favorite = rxMethod<void>(
    pipe(
      filter(() => !this.pending() && !!this.listing()),
      tap(() => patchState(this.state, { pending: true, actionError: '' })),
      exhaustMap(() => {
        const listing = this.listing()!;
        return this.library.favorite(listing.id, !listing.is_favorite).pipe(
          tapResponse({
            next: () => {
              if (this.listing()?.id === listing.id)
                patchState(this.state, {
                  listing: { ...this.listing()!, is_favorite: !listing.is_favorite },
                });
            },
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { actionError: listingError(error) }),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        );
      }),
    ),
  );
  readonly recordHistory = rxMethod<number>(
    pipe(
      exhaustMap((id) =>
        this.api.recordView(id).pipe(
          tapResponse({
            next: () => patchState(this.state, { historyError: '' }),
            error: () =>
              patchState(this.state, {
                historyError:
                  'The listing is available, but your viewing history could not be saved.',
              }),
          }),
        ),
      ),
    ),
  );
  readonly contact = rxMethod<{ id: number; kind: 'call' | 'copy' }>(
    pipe(
      exhaustMap((value) =>
        this.api
          .event(value.id, value.kind)
          .pipe(tapResponse({ next: () => undefined, error: () => undefined })),
      ),
    ),
  );
}
