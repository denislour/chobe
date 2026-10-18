import { ListingSearchPanel } from '@app/listings/search/listing-search-panel';
import { Component, Injector, OnInit, signal, viewChild } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { AttributeFields } from '@app/categories/attribute-fields/attribute-fields';
import { CategoryNav } from '@app/categories/category-nav/category-nav';
import { CategoryData } from '@app/categories/category-types';
import { CategoryStore } from './category.store';

@Component({
  selector: 'app-category-browser',
  imports: [ListingSearchPanel, RouterLink, AttributeFields, CategoryNav],
  providers: [CategoryStore],
  templateUrl: './category-browser.html',
  styleUrls: ['../../shared/styles/categories.css', './category-browser.css'],
})
export class CategoryBrowser implements OnInit {
  protected readonly attributes = viewChild(AttributeFields);
  protected readonly pendingCategory = signal<string | null>(null);
  private readonly selectedId = signal<string | null>(null);

  constructor(
    protected readonly categories: CategoryStore,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly injector: Injector,
  ) {}

  ngOnInit(): void {
    this.categories.load(
      this.route.paramMap.pipe(
        map((params) => {
          const id = params.get('id');
          this.selectedId.set(id);
          return id;
        }),
      ),
      { injector: this.injector },
    );
  }

  protected chooseCategory(id: string | null): void {
    if (id === this.selectedId() || this.categories.pending()) return;
    if (this.attributes()?.form.dirty) {
      this.pendingCategory.set(id ?? '');
      return;
    }
    this.navigate(id);
  }

  protected confirmCategory(): void {
    const id = this.pendingCategory();
    this.pendingCategory.set(null);
    this.navigate(id || null);
  }

  protected reload(): void {
    if (this.attributes()?.form.dirty) this.pendingCategory.set(this.selectedId() ?? '');
    else this.categories.load(this.selectedId());
  }

  protected checkAttributes(): void {
    const form = this.attributes();
    const category = this.categories.category();
    if (!form || !category) return;
    form.form.markAllAsTouched();
    if (form.form.invalid) return;
    this.categories.validate({
      id: category.id,
      version: category.version,
      attributes: form.values(),
    });
  }

  protected breadcrumbs(category: CategoryData): CategoryData[] {
    const parents: CategoryData[] = [];
    let parent = this.categories.categories().find((item) => item.id === category.parent);
    while (parent && parents.length < 4) {
      parents.unshift(parent);
      parent = this.categories.categories().find((item) => item.id === parent?.parent);
    }
    return parents;
  }

  protected children(): CategoryData[] {
    return this.categories
      .categories()
      .filter(
        (item) =>
          item.parent === this.categories.category()?.id ||
          (!this.categories.category() && item.parent === null),
      );
  }

  private navigate(id: string | null): void {
    if (id === this.selectedId()) this.categories.load(id);
    else void this.router.navigate(id ? ['/categories', id] : ['/categories']);
  }
}
