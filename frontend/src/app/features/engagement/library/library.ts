import { Component, Injector, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { ListingCard } from '@app/domain/listing/listing-card/listing-card';
import { MarketplaceNav } from '@app/layouts/marketplace-nav/marketplace-nav';
import { LibraryStore } from './library.store';
@Component({
  selector: 'app-library',
  imports: [RouterLink, ListingCard, MarketplaceNav],
  providers: [LibraryStore],
  templateUrl: './library.html',
  styleUrl: './library.css',
})
export class Library implements OnInit {
  protected readonly mode = signal<'favorites' | 'history'>('favorites');
  protected readonly page = signal(1);
  protected readonly confirmation = signal(false);
  constructor(
    protected readonly library: LibraryStore,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly injector: Injector,
  ) {}
  ngOnInit(): void {
    this.library.load(
      this.route.queryParamMap.pipe(
        map((params) => {
          const mode = params.get('tab') === 'history' ? 'history' : 'favorites';
          const page = Number(params.get('page') ?? 1);
          this.mode.set(mode);
          this.page.set(page);
          this.confirmation.set(false);
          return { mode, page };
        }),
      ),
      { injector: this.injector },
    );
  }
  protected changePage(delta: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: this.page() + delta },
      queryParamsHandling: 'merge',
    });
  }
  protected clear(): void {
    this.confirmation.set(false);
    this.library.clear();
  }
}
