import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, pipe, switchMap, tap } from 'rxjs';
import { accountError, FieldErrors } from '@app/accounts/account-errors';
import { ShopApi, ShopData, ShopSaveRequest, ShopStatusRequest } from './shop-api';

interface ShopState {
  shop: ShopData | null;
  loaded: boolean;
  loading: boolean;
  pending: boolean;
  error: string;
  fieldErrors: FieldErrors;
  notice: string;
}

@Injectable()
export class ShopStore {
  private readonly state = signalState<ShopState>({
    shop: null,
    loaded: false,
    loading: false,
    pending: false,
    error: '',
    fieldErrors: {},
    notice: '',
  });
  readonly shop = this.state.shop;
  readonly loaded = this.state.loaded;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly fieldErrors = this.state.fieldErrors;
  readonly notice = this.state.notice;

  constructor(private readonly api: ShopApi) {}

  readonly load = rxMethod<void>(
    pipe(
      filter(() => !this.pending()),
      switchMap(() => {
        patchState(this.state, { loading: true, error: '', fieldErrors: {}, notice: '' });
        return this.api.mine().pipe(
          tapResponse({
            next: (shop) => patchState(this.state, { shop, loaded: true }),
            error: (error: HttpErrorResponse) => {
              if (error.status === 404) {
                patchState(this.state, { shop: null, loaded: true });
              } else {
                patchState(this.state, {
                  ...accountError(error),
                  ...(error.status === 403 ? { shop: null, loaded: false } : {}),
                });
              }
            },
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );

  readonly save = rxMethod<ShopSaveRequest>(
    pipe(
      filter(() => this.loaded() && !this.pending() && !this.loading()),
      tap(() => this.startMutation()),
      exhaustMap((request) =>
        this.api.save(request).pipe(
          tapResponse({
            next: (shop) => patchState(this.state, { shop, notice: 'Shop saved.' }),
            error: (error: HttpErrorResponse) => patchState(this.state, accountError(error)),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  readonly changeStatus = rxMethod<ShopStatusRequest>(
    pipe(
      filter(() => !this.pending() && !this.loading()),
      tap(() => this.startMutation()),
      exhaustMap((request) =>
        this.api.changeStatus(request).pipe(
          tapResponse({
            next: (shop) => patchState(this.state, { shop, notice: 'Shop status updated.' }),
            error: (error: HttpErrorResponse) => patchState(this.state, accountError(error)),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  private startMutation(): void {
    patchState(this.state, { pending: true, error: '', fieldErrors: {}, notice: '' });
  }
}
