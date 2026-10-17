import { Component, Injector, OnInit, computed, signal, viewChild } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { CategoryStore } from '@app/categories/browse/category.store';
import { AttributeFields } from '@app/categories/attribute-fields/attribute-fields';
import { AttributeValues } from '@app/categories/category-types';
import { ListingCard } from '@app/listings/listing-card/listing-card';
import { MarketplaceNav } from '@app/listings/marketplace-nav/marketplace-nav';
import { SearchFilters } from '@app/listings/listing-types';
import { SearchStore } from './search.store';
@Component({
  selector: 'app-search',
  imports: [ReactiveFormsModule, RouterLink, AttributeFields, ListingCard, MarketplaceNav],
  providers: [SearchStore, CategoryStore],
  templateUrl: './search.html',
  styleUrl: './search.css',
})
export class Search implements OnInit {
  private readonly attributeForm = viewChild(AttributeFields);
  protected readonly current = signal<SearchFilters>({});
  protected readonly initialAttributes = signal<AttributeValues>({});
  protected readonly categoryId = signal('');
  protected readonly urlError = signal('');
  protected readonly fields = computed(
    () =>
      this.categories
        .categories()
        .find((item) => item.id === this.categoryId())
        ?.attributes.filter((field) => field.filterable)
        .map((field) => ({ ...field, required: false })) ?? [],
  );
  protected readonly form;
  constructor(
    protected readonly search: SearchStore,
    protected readonly categories: CategoryStore,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly injector: Injector,
    fb: FormBuilder,
  ) {
    this.form = fb.group({
      q: fb.nonNullable.control(''),
      category: fb.nonNullable.control(''),
      location: fb.nonNullable.control(''),
      condition: fb.nonNullable.control(''),
      price_min: fb.control<number | null>(null),
      price_max: fb.control<number | null>(null),
      sort: fb.nonNullable.control('newest'),
    });
  }
  ngOnInit(): void {
    this.categories.load(null);
    this.search.load(
      this.route.queryParamMap.pipe(
        map((params) => {
          const filters: SearchFilters = {};
          for (const key of ['q', 'category', 'shop', 'location', 'condition', 'sort'] as const) {
            const value = params.get(key);
            if (value) filters[key] = value;
          }
          for (const key of ['price_min', 'price_max', 'page'] as const) {
            const value = params.get(key);
            if (value) filters[key] = Number(value);
          }
          this.urlError.set('');
          try {
            const attributes = JSON.parse(params.get('attributes') ?? '{}') as AttributeValues;
            if (!attributes || Array.isArray(attributes) || typeof attributes !== 'object')
              throw new Error();
            filters.attributes = attributes;
          } catch {
            this.urlError.set(
              'The attribute filters in this link are invalid. Clear the filters to continue.',
            );
          }
          this.current.set(filters);
          this.categoryId.set(filters.category ?? '');
          this.initialAttributes.set(filters.attributes ?? {});
          this.form.patchValue({
            q: filters.q ?? '',
            category: filters.category ?? '',
            location: filters.location ?? '',
            condition: filters.condition ?? '',
            sort: filters.sort ?? 'newest',
            price_min: filters.price_min ?? null,
            price_max: filters.price_max ?? null,
          });
          return filters;
        }),
      ),
      { injector: this.injector },
    );
  }
  protected apply(): void {
    const values = this.form.getRawValue();
    const attributes = this.attributeForm()?.values() ?? {};
    const clean = Object.fromEntries(
      Object.entries(attributes).filter(([, value]) => value !== null && value !== ''),
    );
    void this.router.navigate(['/search'], {
      queryParams: {
        ...values,
        shop: this.current().shop ?? null,
        attributes: Object.keys(clean).length ? JSON.stringify(clean) : null,
        page: null,
      },
    });
  }
  protected changeCategory(): void {
    this.categoryId.set(this.form.controls.category.value);
    this.initialAttributes.set({});
  }
  protected clear(): void {
    void this.router.navigate(['/search'], { queryParams: { q: this.current().q ?? null } });
  }
  protected page(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page },
      queryParamsHandling: 'merge',
    });
  }
}
