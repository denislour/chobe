import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { EMPTY, exhaustMap, filter, pipe, switchMap, tap } from 'rxjs';
import { StorefrontData } from '@app/data-access/shops/storefront-api';
import { FollowedShopsApi } from './followed-shops-api';

interface FollowingQuery {
  page: number;
  viewerId: number | null;
}

interface FollowingState {
  shops: StorefrontData[];
  viewerId: number | null;
  page: number;
  count: number;
  hasNext: boolean;
  hasPrevious: boolean;
  loading: boolean;
  pending: boolean;
  error: string;
  notice: string;
}

const loadErrors: Record<number, string> = {
  403: 'Log in again to see the shops you follow.',
  404: 'This page is no longer available. Reload shops to return to the first page.',
  429: 'Too many requests. Please wait a moment and reload shops.',
};
const mutationErrors: Record<number, string> = {
  403: 'Your security check expired. Reload the page and log in again.',
  429: 'Too many changes. Please wait a moment and try again.',
};

@Injectable()
export class FollowedShopsStore {
  private readonly state = signalState<FollowingState>({
    shops: [], viewerId: null, page: 1, count: 0, hasNext: false, hasPrevious: false,
    loading: false, pending: false, error: '', notice: '',
  });
  readonly shops = this.state.shops;
  readonly page = this.state.page;
  readonly count = this.state.count;
  readonly hasNext = this.state.hasNext;
  readonly hasPrevious = this.state.hasPrevious;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly notice = this.state.notice;

  constructor(private readonly api: FollowedShopsApi) {}

  readonly load = rxMethod<FollowingQuery>(
    pipe(
      switchMap(({ page, viewerId }) => {
        patchState(this.state, {
          viewerId, page, shops: [], count: 0, hasNext: false, hasPrevious: false,
          loading: viewerId !== null, error: '', notice: '',
        });
        if (viewerId === null) return EMPTY;
        return this.api.list(page).pipe(
          tapResponse({
            next: (response) => patchState(this.state, {
              shops: response.results, count: response.count,
              hasNext: response.next !== null, hasPrevious: response.previous !== null,
            }),
            error: (error: HttpErrorResponse) => this.failLoad(error),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );

  readonly unfollow = rxMethod<string>(
    pipe(
      filter((id) => !this.pending() && !this.loading() && this.state.viewerId() !== null
        && this.shops().some((shop) => shop.id === id)),
      tap(() => patchState(this.state, { pending: true, error: '', notice: '' })),
      exhaustMap((id) => {
        const viewerId = this.state.viewerId();
        return this.api.setFollowing(id, false).pipe(
          tapResponse({
            next: () => this.finishUnfollow(viewerId),
            error: (error: HttpErrorResponse) => this.failUnfollow(viewerId, error),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        );
      }),
    ),
  );

  private finishUnfollow(viewerId: number | null): void {
    if (viewerId !== this.state.viewerId()) return;
    const page = this.shops().length === 1 ? Math.max(1, this.page() - 1) : this.page();
    this.load({ page, viewerId });
    patchState(this.state, { notice: 'You unfollowed the shop.' });
  }

  private failLoad(error: HttpErrorResponse): void {
    patchState(this.state, {
      error: loadErrors[error.status] ?? 'Unable to load your followed shops. Please try again.',
    });
  }

  private failUnfollow(viewerId: number | null, error: HttpErrorResponse): void {
    if (viewerId !== this.state.viewerId()) return;
    patchState(this.state, {
      error: mutationErrors[error.status] ?? 'Unable to unfollow this shop. Please try again.',
    });
  }
}
