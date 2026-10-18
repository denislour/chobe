import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { pipe, switchMap } from 'rxjs';
import { ShopApi, ShopData } from '@app/data-access/shops/shop-api';

interface ShopPreviewState {
  shop: ShopData | null;
  loading: boolean;
  error: string;
}

const previewErrors: Record<number, string> = {
  403: 'Log in to preview your shop.',
  404: 'This shop preview was not found.',
};

@Injectable()
export class ShopPreviewStore {
  private readonly state = signalState<ShopPreviewState>({
    shop: null,
    loading: false,
    error: '',
  });
  readonly shop = this.state.shop;
  readonly loading = this.state.loading;
  readonly error = this.state.error;

  constructor(private readonly api: ShopApi) {}

  readonly load = rxMethod<string>(
    pipe(
      switchMap((slug) => {
        patchState(this.state, { shop: null, loading: true, error: '' });
        return this.api.preview(slug).pipe(
          tapResponse({
            next: (shop) => patchState(this.state, { shop }),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, {
                error: previewErrors[error.status] ?? 'Unable to load the preview. Try again.',
              }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );
}
