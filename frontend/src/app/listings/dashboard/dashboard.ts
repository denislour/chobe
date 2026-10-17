import { DatePipe } from '@angular/common';
import { Component, Injector, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { MarketplaceNav } from '@app/listings/marketplace-nav/marketplace-nav';
import { listingPrice } from '@app/listings/listing-types';
import { DashboardStore, OwnerAction } from './dashboard.store';
import { OwnerFilters } from './listing-management-api';
@Component({
  selector: 'app-dashboard',
  imports: [DatePipe, RouterLink, ReactiveFormsModule, MarketplaceNav],
  providers: [DashboardStore],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard implements OnInit {
  protected readonly form;
  protected readonly filters = signal<OwnerFilters>({ state: '', q: '', page: 1, retention: '' });
  protected readonly confirmation = signal<OwnerAction | null>(null);
  protected readonly statuses = ['draft', 'pending', 'rejected', 'active', 'hidden', 'sold'];
  protected readonly price = listingPrice;
  constructor(
    protected readonly dashboard: DashboardStore,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly injector: Injector,
    fb: FormBuilder,
  ) {
    this.form = fb.nonNullable.group({ state: [''], q: [''], retention: [''] });
  }
  ngOnInit(): void {
    this.dashboard.load(
      this.route.queryParamMap.pipe(
        map((params) => {
          const filters = {
            state: params.get('state') ?? '',
            q: params.get('q') ?? '',
            retention: params.get('retention') ?? '',
            page: Number(params.get('page') ?? 1),
          };
          this.filters.set(filters);
          this.form.patchValue(filters);
          return filters;
        }),
      ),
      { injector: this.injector },
    );
  }
  protected apply(): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { ...this.form.getRawValue(), page: null },
    });
  }
  protected page(value: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: value },
      queryParamsHandling: 'merge',
    });
  }
  protected confirm(): void {
    const action = this.confirmation();
    this.confirmation.set(null);
    if (action) this.dashboard.change(action);
  }
}
