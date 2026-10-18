import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, effect, signal, viewChild } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AttributeFields } from '@app/domain/category/attribute-fields/attribute-fields';
import { CategoryStore } from '@app/domain/category/category.store';
import { AttributeValues } from '@app/domain/category/category-types';
import { MarketplaceNav } from '@app/listings/marketplace-nav/marketplace-nav';
import { SavedSearch } from '@app/data-access/engagement/alerts-api';
import { AlertsStore } from '@app/domain/engagement/alerts.store';
@Component({
  selector: 'app-alerts',
  imports: [AttributeFields, DatePipe, ReactiveFormsModule, RouterLink, MarketplaceNav],
  providers: [AlertsStore, CategoryStore],
  templateUrl: './alerts.html',
  styleUrl: './alerts.css',
})
export class Alerts implements OnInit {
  private readonly attributeForm = viewChild(AttributeFields);
  protected readonly categoryId = signal('');
  protected readonly initialAttributes = signal<AttributeValues>({});
  protected readonly fields = computed(
    () =>
      this.categories
        .categories()
        .find((item) => item.id === this.categoryId())
        ?.attributes.filter((field) => field.filterable)
        .map((field) => ({ ...field, required: false })) ?? [],
  );
  protected readonly preferencesForm;
  protected readonly searchForm;
  protected readonly editing = signal<SavedSearch | null>(null);
  protected readonly deleting = signal<number | null>(null);
  protected readonly page = signal(1);
  protected readonly filterError = signal('');
  constructor(
    protected readonly alerts: AlertsStore,
    protected readonly categories: CategoryStore,
    fb: FormBuilder,
  ) {
    this.preferencesForm = fb.nonNullable.group({ inbox: [false], email: [false] });
    this.searchForm = fb.group({
      name: fb.nonNullable.control('', Validators.required),
      frequency: fb.nonNullable.control('daily'),
      active: fb.nonNullable.control(true),
      q: fb.nonNullable.control(''),
      category: fb.nonNullable.control(''),
      location: fb.nonNullable.control(''),
      condition: fb.nonNullable.control(''),
      price_min: fb.control<number | null>(null),
      price_max: fb.control<number | null>(null),
    });
    effect(() => {
      const editing = this.editing();
      const searches = this.alerts.searches();
      if (!editing || this.alerts.loading() || this.alerts.error()) return;
      const latest = searches.find((search) => search.id === editing.id);
      if (latest && latest.version !== editing.version) this.editing.set(latest);
      else if (!latest) this.editing.set(null);
    });
    effect(() => {
      const preferences = this.alerts.preferences();
      if (preferences)
        this.preferencesForm.reset({ inbox: preferences.inbox, email: preferences.email });
    });
  }
  ngOnInit(): void {
    this.alerts.load(1);
    this.categories.load(null);
  }
  protected savePreferences(): void {
    const current = this.alerts.preferences();
    if (current)
      this.alerts.change({
        kind: 'preferences',
        values: { ...this.preferencesForm.getRawValue(), version: current.version },
      });
  }
  protected edit(search: SavedSearch): void {
    this.editing.set(search);
    this.filterError.set('');
    this.categoryId.set(search.filters.category ?? '');
    this.initialAttributes.set(search.filters.attributes ?? {});
    this.searchForm.reset({
      name: search.name,
      frequency: search.frequency,
      active: search.active,
      q: search.filters.q ?? '',
      category: search.filters.category ?? '',
      location: search.filters.location ?? '',
      condition: search.filters.condition ?? '',
      price_min: search.filters.price_min ?? null,
      price_max: search.filters.price_max ?? null,
    });
  }
  protected changeCategory(): void {
    this.categoryId.set(this.searchForm.controls.category.value);
    this.initialAttributes.set({});
  }
  protected saveSearch(): void {
    const current = this.editing();
    if (!current || this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }
    const { name, frequency, active, ...values } = this.searchForm.getRawValue();
    const attributes = Object.fromEntries(
      Object.entries(this.attributeForm()?.values() ?? {}).filter(
        ([, value]) => value !== null && value !== '',
      ),
    );
    const filters = {
      ...Object.fromEntries(
        Object.entries(values).filter(([, value]) => value !== null && value !== ''),
      ),
      ...(current.filters.shop ? { shop: current.filters.shop } : {}),
      ...(Object.keys(attributes).length ? { attributes } : {}),
    };
    this.alerts.save({
      id: current.id,
      values: {
        name,
        frequency: frequency as 'daily' | 'immediate',
        active,
        filters,
        version: current.version,
      },
    });
  }
  protected searchParams(search: SavedSearch): Record<string, string | number | null> {
    return Object.fromEntries(
      Object.entries(search.filters).map(([key, value]) => [
        key,
        typeof value === 'object' ? JSON.stringify(value) : (value ?? null),
      ]),
    );
  }
  protected changePage(delta: number): void {
    this.page.update((value) => value + delta);
    this.alerts.load(this.page());
  }
}
