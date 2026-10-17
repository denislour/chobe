import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MarketplaceNav } from '@app/listings/marketplace-nav/marketplace-nav';
import { ListingCard } from '@app/listings/listing-card/listing-card';
import { HomeStore } from './home.store';
@Component({
  selector: 'app-home',
  imports: [RouterLink, MarketplaceNav, ListingCard],
  providers: [HomeStore],
  templateUrl: './home.html',
  styleUrl: './home.css',
})
export class Home implements OnInit {
  constructor(protected readonly home: HomeStore) {}
  ngOnInit(): void {
    this.home.loadCategories();
    this.home.loadListings();
  }
}
