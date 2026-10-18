import { ListingSearchPanel } from '@app/listings/search/listing-search-panel';
import { ReportForm } from '@app/listings/report-form/report-form';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, Injector, effect, OnInit, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { combineLatest, map } from 'rxjs';
import { AuthStore } from '@app/auth/auth.store';
import { ShopNav } from '@app/shops/shop-nav/shop-nav';
import { StorefrontStore } from './storefront.store';

@Component({
  selector: 'app-shop-storefront',
  imports: [ListingSearchPanel, ReportForm, DatePipe, RouterLink, ShopNav],
  providers: [StorefrontStore],
  templateUrl: './shop-storefront.html',
  styleUrls: ['../../shared/styles/shops.css', './shop-storefront.css'],
})
export class ShopStorefront implements OnInit {
  protected readonly slug = signal('');
  protected readonly tab;
  private readonly viewer;

  constructor(
    protected readonly storefront: StorefrontStore,
    protected readonly auth: AuthStore,
    private readonly route: ActivatedRoute,
    private readonly injector: Injector,
    private readonly router: Router,
    title: Title,
    destroyRef: DestroyRef,
  ) {
    this.viewer = toObservable(auth.user);
    this.tab = toSignal(
      route.queryParamMap.pipe(
        map((params) => (params.get('tab') === 'about' ? 'about' : 'listings')),
      ),
      { initialValue: 'listings' },
    );
    effect(() => {
      const shop = this.storefront.shop();
      title.setTitle(shop ? `${shop.name} · Chobe` : 'Shop · Chobe');
      if (shop && this.slug() !== shop.slug) {
        void this.router.navigate(['/shops', shop.slug], {
          queryParamsHandling: 'preserve',
          replaceUrl: true,
        });
      }
    });
    destroyRef.onDestroy(() => title.setTitle('Chobe'));
  }

  ngOnInit(): void {
    this.storefront.load(
      combineLatest([this.route.paramMap, this.viewer]).pipe(
        map(([params, user]) => {
          const slug = params.get('slug') ?? '';
          this.slug.set(slug);
          return { slug, viewerId: user?.id ?? null };
        }),
      ),
      { injector: this.injector },
    );
  }

  protected retry(): void {
    this.storefront.load({ slug: this.slug(), viewerId: this.auth.user()?.id ?? null });
  }

  protected follow(): void {
    const user = this.auth.user();
    const shop = this.storefront.shop();
    if (!user || this.auth.sessionError()) {
      void this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    if (shop)
      this.storefront.changeFollowing({
        shopId: shop.id,
        viewerId: user.id,
        following: !shop.is_following,
      });
  }
}
