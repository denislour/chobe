import { DatePipe } from '@angular/common';
import { Component, DestroyRef, Injector, OnInit, effect, signal } from '@angular/core';
import { Meta, Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { AuthStore } from '@app/auth/auth.store';
import { ComparisonStore } from '@app/listings/comparison/comparison.store';
import { listingPrice } from '@app/listings/listing-types';
import { MarketplaceNav } from '@app/listings/marketplace-nav/marketplace-nav';
import { DetailStore } from './detail.store';
@Component({
  selector: 'app-detail',
  imports: [DatePipe, RouterLink, MarketplaceNav],
  providers: [DetailStore],
  templateUrl: './detail.html',
  styleUrl: './detail.css',
})
export class Detail implements OnInit {
  protected readonly activeImage = signal(0);
  protected readonly reportOpen = signal(false);
  protected readonly copyMessage = signal('');
  protected readonly price = listingPrice;
  constructor(
    protected readonly detail: DetailStore,
    protected readonly comparison: ComparisonStore,
    private readonly auth: AuthStore,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly injector: Injector,
    title: Title,
    meta: Meta,
    destroyRef: DestroyRef,
  ) {
    effect(() => {
      const listing = this.detail.listing();
      title.setTitle(listing ? `${listing.title} · Chobe` : 'Listing · Chobe');
      meta.updateTag({
        name: 'description',
        content: listing?.description.slice(0, 160) ?? 'Find useful items on Chobe.',
      });
    });
    destroyRef.onDestroy(() => {
      title.setTitle('Chobe');
      meta.removeTag('name="description"');
    });
  }
  ngOnInit(): void {
    this.detail.load(
      this.route.paramMap.pipe(
        map((params) => {
          this.activeImage.set(0);
          this.copyMessage.set('');
          this.reportOpen.set(false);
          return { id: Number(params.get('id')), record: !!this.auth.user() };
        }),
      ),
      { injector: this.injector },
    );
  }
  protected retry(): void {
    this.detail.load({
      id: Number(this.route.snapshot.paramMap.get('id')),
      record: !!this.auth.user(),
    });
  }
  protected favorite(): void {
    if (!this.auth.user()) {
      void this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    this.detail.favorite();
  }
  protected contact(): void {
    const listing = this.detail.listing();
    if (listing) this.detail.contact({ id: listing.id, kind: 'call' });
  }
  protected async copyPhone(): Promise<void> {
    const listing = this.detail.listing();
    if (!listing?.phone) return;
    try {
      await navigator.clipboard.writeText(listing.phone);
      this.copyMessage.set('Phone number copied.');
      this.detail.contact({ id: listing.id, kind: 'copy' });
    } catch {
      this.copyMessage.set('Copy is unavailable. Select the phone number and copy it manually.');
    }
  }
  protected async share(): Promise<void> {
    try {
      await navigator.clipboard.writeText(window.location.href);
      this.copyMessage.set('Listing link copied.');
    } catch {
      this.copyMessage.set('Copy the page address from your browser to share this listing.');
    }
  }
}
