import { Component, effect, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ListingCard } from '@app/domain/listing/listing-card/listing-card';
import { SearchStore } from './search.store';
@Component({
  selector: 'app-listing-search-panel',
  imports: [RouterLink, ListingCard],
  providers: [SearchStore],
  template:
    '@if(search.loading()){<p role="status">Loading listings…</p>}@if(search.error()){<p class="error" role="alert">{{search.error()}}</p><button type="button" (click)="load()">Try again</button>}<div class="product-grid">@for(listing of search.listings();track listing.id){<app-listing-card [listing]="listing" />}</div>@if(!search.loading()&&!search.error()&&!search.listings().length){<p class="feedback">No public listings yet.</p>}@if(search.count()>20){<a routerLink="/search" [queryParams]="{shop:shopId(),category:categoryId()}">Browse all {{search.count()}} listings</a>}',
  styleUrls: ['../../../shared/styles/marketplace.css'],
})
export class ListingSearchPanel {
  readonly shopId = input<string | null>(null);
  readonly categoryId = input<string | null>(null);
  constructor(protected readonly search: SearchStore) {
    effect(() =>
      this.search.load({
        ...(this.shopId() ? { shop: this.shopId()! } : {}),
        ...(this.categoryId() ? { category: this.categoryId()! } : {}),
      }),
    );
  }
  protected load(): void {
    this.search.load({
      ...(this.shopId() ? { shop: this.shopId()! } : {}),
      ...(this.categoryId() ? { category: this.categoryId()! } : {}),
    });
  }
}
