import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { categoryFixture } from '@app/categories/category-fixtures';
import { CategoryStore } from './category.store';

describe('CategoryStore', () => {
  let store: CategoryStore;
  let http: HttpTestingController;
  const detail = `/api/v1/categories/${categoryFixture.id}/`;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CategoryStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(CategoryStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  function loadCategory(): void {
    store.load(categoryFixture.id);
    http.expectOne('/api/v1/categories/').flush([categoryFixture]);
    http.expectOne(detail).flush(categoryFixture);
    http
      .expectOne(`${detail}facets/`)
      .flush({ category_id: categoryFixture.id, version: 2, fields: [] });
  }

  it('shows an empty directory and can retry after a read error', () => {
    store.load(null);
    http.expectOne('/api/v1/categories/').flush({}, { status: 503, statusText: 'Unavailable' });
    expect(store.loading()).toBe(false);
    expect(store.error()).toContain('try again');
    store.load(null);
    http.expectOne('/api/v1/categories/').flush([]);
    expect(store.error()).toBe('');
    expect(store.categories()).toEqual([]);
  });

  it('asks for a reload if the schema changes between detail and facet reads', () => {
    store.load(categoryFixture.id);
    http.expectOne('/api/v1/categories/').flush([categoryFixture]);
    http.expectOne(detail).flush(categoryFixture);
    http
      .expectOne(`${detail}facets/`)
      .flush({ category_id: categoryFixture.id, version: 4, fields: [] });
    expect(store.category()).toBeNull();
    expect(store.error()).toContain('changed while loading');
    expect(store.loading()).toBe(false);
  });

  it('prevents duplicate checks and keeps the schema visible after a conflict', () => {
    loadCategory();
    const check = {
      id: categoryFixture.id,
      version: 2,
      attributes: { storage_gb: 128, tested: false },
    };
    store.validate(check);
    store.validate(check);
    http
      .expectOne(`${detail}validate-attributes/`)
      .flush({}, { status: 409, statusText: 'Conflict' });
    expect(store.category()).toEqual(categoryFixture);
    expect(store.pending()).toBe(false);
    expect(store.validationError()).toContain('Reload');
    store.validate(check);
    http
      .expectOne(`${detail}validate-attributes/`)
      .flush({ category_id: check.id, version: 2, attributes: check.attributes });
    expect(store.notice()).toContain('match');
    store.clearValidation();
    expect(store.notice()).toBe('');
  });

  it('does not apply a late attribute error to a different category', () => {
    loadCategory();
    store.validate({ id: categoryFixture.id, version: 2, attributes: {} });
    const check = http.expectOne(`${detail}validate-attributes/`);
    store.load(null);
    http.expectOne('/api/v1/categories/').flush([categoryFixture]);
    check.flush(
      { attributes: { tested: ['Required.'] } },
      { status: 400, statusText: 'Bad Request' },
    );
    expect(store.validationError()).toBe('');
    expect(store.fieldErrors()).toEqual({});
    expect(store.pending()).toBe(false);
  });
});
