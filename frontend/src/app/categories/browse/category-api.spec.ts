import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { categoryFixture } from '@app/categories/category-fixtures';
import { CategoryApi } from './category-api';

describe('CategoryApi', () => {
  let api: CategoryApi;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(CategoryApi);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('reads categories, the published schema and its facets', () => {
    api.list().subscribe();
    api.retrieve(categoryFixture.id).subscribe();
    api.facets(categoryFixture.id).subscribe();
    http.expectOne('/api/v1/categories/').flush([categoryFixture]);
    http.expectOne(`/api/v1/categories/${categoryFixture.id}/`).flush(categoryFixture);
    http
      .expectOne(`/api/v1/categories/${categoryFixture.id}/facets/`)
      .flush({ category_id: categoryFixture.id, version: 2, fields: [] });
  });

  it('validates canonical attributes against the version loaded by the form', () => {
    api.validate(categoryFixture.id, 2, { storage_gb: 128, tested: false }).subscribe();
    const request = http.expectOne(`/api/v1/categories/${categoryFixture.id}/validate-attributes/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      version: 2,
      attributes: { storage_gb: 128, tested: false },
    });
    request.flush({ category_id: categoryFixture.id, ...request.request.body });
  });
});
