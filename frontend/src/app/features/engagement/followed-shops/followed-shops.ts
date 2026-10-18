import { Component, effect, OnInit } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { AuthStore } from '@app/auth/auth.store';
import { ShopNav } from '@app/layouts/shop-nav/shop-nav';
import { FollowedShopsStore } from './followed-shops.store';

@Component({
  selector: 'app-followed-shops',
  imports: [RouterLink, ShopNav],
  providers: [FollowedShopsStore],
  templateUrl: './followed-shops.html',
  styleUrls: ['../../../shared/styles/shops.css', './followed-shops.css'],
})
export class FollowedShops implements OnInit {
  private readonly viewer;

  constructor(
    protected readonly following: FollowedShopsStore,
    protected readonly auth: AuthStore,
    router: Router,
  ) {
    this.viewer = toObservable(auth.user);
    effect(() => {
      if (!this.auth.user() && !this.auth.pending()) {
        this.following.load({ page: 1, viewerId: null });
        void router.navigate(['/login'], { queryParams: { returnUrl: '/account/followed-shops' } });
      }
    });
  }

  ngOnInit(): void {
    this.following.load(this.viewer.pipe(map((user) => ({ page: 1, viewerId: user?.id ?? null }))));
  }

  protected loadPage(page: number): void {
    if (this.following.pending() || this.following.loading()) return;
    this.following.load({ page, viewerId: this.auth.user()?.id ?? null });
  }
}
