import { Component, Injector, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { MarketplaceNav } from '@app/listings/marketplace-nav/marketplace-nav';
import { listingPrice } from '@app/domain/listing/listing-types';
import { ComparisonPageStore } from './comparison-page.store';
import { ComparisonStore } from './comparison.store';
@Component({
  selector: 'app-comparison',
  imports: [RouterLink, MarketplaceNav],
  providers: [ComparisonPageStore],
  templateUrl: './comparison.html',
  styleUrl: './comparison.css',
})
export class Comparison implements OnInit {
  protected readonly ids = signal('');
  protected readonly price = listingPrice;
  constructor(
    protected readonly comparison: ComparisonPageStore,
    private readonly selected: ComparisonStore,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly injector: Injector,
  ) {}
  ngOnInit(): void {
    this.comparison.load(
      this.route.queryParamMap.pipe(
        map((params) => {
          const ids = params.get('ids') ?? this.selected.ids().join(',');
          this.ids.set(ids);
          return ids;
        }),
      ),
      { injector: this.injector },
    );
  }
  protected remove(id: number): void {
    const ids = this.ids()
      .split(',')
      .filter((value) => value !== String(id))
      .join(',');
    if (this.selected.ids().includes(id)) this.selected.toggle(id);
    void this.router.navigate(['/compare'], { queryParams: { ids: ids || null } });
  }
  protected clear(): void {
    this.selected.clear();
    void this.router.navigate(['/compare']);
  }
}
