import { Component, input } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthStore } from '@app/auth/auth.store';
import { ComparisonStore } from '@app/domain/listing/comparison.store';
import { PublicListing, listingPrice } from '@app/domain/listing/listing-types';
import { ListingCardStore } from './listing-card.store';
@Component({
  selector: 'app-listing-card',
  imports: [RouterLink],
  providers: [ListingCardStore],
  templateUrl: './listing-card.html',
  styleUrl: './listing-card.css',
})
export class ListingCard {
  readonly listing = input.required<PublicListing>();
  protected readonly price = listingPrice;
  constructor(
    protected readonly card: ListingCardStore,
    protected readonly comparison: ComparisonStore,
    private readonly auth: AuthStore,
    private readonly router: Router,
  ) {}
  protected favorite(): void {
    if (!this.auth.user()) {
      void this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    this.card.favorite({
      id: this.listing().id,
      saved: !(this.card.saved() ?? this.listing().is_favorite),
    });
  }
}
