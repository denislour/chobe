import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, pipe, switchMap, tap } from 'rxjs';
import { FollowedShopsApi } from '@app/shops/followed-shops/followed-shops-api';
import { StorefrontApi, StorefrontData } from '@app/data-access/shops/storefront-api';

interface StorefrontQuery {
  slug: string;
  viewerId: number | null;
}

interface FollowingChange {
  shopId: string;
  viewerId: number;
  following: boolean;
}

interface StorefrontState {
  shop: StorefrontData | null;
  viewerId: number | null;
  loading: boolean;
  pending: boolean;
  error: string;
  followError: string;
  notice: string;
}

const readErrors: Record<number, string> = {
  404: 'This shop is not available.',
  429: 'Too many requests. Please try again later.',
};
const followErrors: Record<number, string> = {
  403: 'Your security check expired. Reload the page and log in again.',
  429: 'Too many changes. Please wait a moment and try again.',
};

@Injectable()
export class StorefrontStore {
  private readonly state = signalState<StorefrontState>({
    shop: null,
    viewerId: null,
    loading: false,
    pending: false,
    error: '',
    followError: '',
    notice: '',
  });
  readonly shop = this.state.shop;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly followError = this.state.followError;
  readonly notice = this.state.notice;

  constructor(
    private readonly api: StorefrontApi,
    private readonly followingApi: FollowedShopsApi,
  ) {}

  readonly load = rxMethod<StorefrontQuery>(
    pipe(
      switchMap(({ slug, viewerId }) => {
        patchState(this.state, {
          shop: null, viewerId, loading: true, error: '', followError: '', notice: '',
        });
        return this.api.retrieve(slug).pipe(
          tapResponse({
            next: (shop) => patchState(this.state, { shop }),
            error: (error: HttpErrorResponse) => patchState(this.state, {
              error: readErrors[error.status] ?? 'Unable to load this shop. Please try again.',
            }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );

  readonly changeFollowing = rxMethod<FollowingChange>(
    pipe(
      filter((change) => !this.pending() && !this.loading() && this.isCurrent(change)),
      tap(() => patchState(this.state, { pending: true, followError: '', notice: '' })),
      exhaustMap((change) => this.followingApi.setFollowing(change.shopId, change.following).pipe(
        tapResponse({
          next: () => this.finishFollowing(change),
          error: (error: HttpErrorResponse) => this.failFollowing(change, error),
          finalize: () => patchState(this.state, { pending: false }),
        }),
      )),
    ),
  );

  private isCurrent(change: FollowingChange): boolean {
    return this.shop()?.id === change.shopId && this.state.viewerId() === change.viewerId;
  }

  private finishFollowing(change: FollowingChange): void {
    const shop = this.shop();
    if (!shop || !this.isCurrent(change)) return;
    patchState(this.state, {
      shop: { ...shop, is_following: change.following },
      notice: change.following ? 'You are now following this shop.' : 'You unfollowed this shop.',
    });
  }

  private failFollowing(change: FollowingChange, error: HttpErrorResponse): void {
    if (!this.isCurrent(change)) return;
    if (error.status === 404) {
      patchState(this.state, { shop: null, error: readErrors[404] });
      return;
    }
    patchState(this.state, {
      followError: followErrors[error.status] ?? 'Unable to update following. Please try again.',
    });
  }
}
