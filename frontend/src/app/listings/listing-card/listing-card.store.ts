import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, pipe, tap } from 'rxjs';
import { LibraryApi } from '@app/listings/library/library-api';
import { listingError } from '@app/shared/errors/listing-errors';
interface CardState {
  saved: boolean | null;
  pending: boolean;
  error: string;
}
@Injectable()
export class ListingCardStore {
  private readonly state = signalState<CardState>({ saved: null, pending: false, error: '' });
  readonly saved = this.state.saved;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  constructor(private readonly api: LibraryApi) {}
  readonly favorite = rxMethod<{ id: number; saved: boolean }>(
    pipe(
      filter(() => !this.pending()),
      tap(() => patchState(this.state, { pending: true, error: '' })),
      exhaustMap((value) =>
        this.api.favorite(value.id, value.saved).pipe(
          tapResponse({
            next: () => patchState(this.state, { saved: value.saved }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );
}
