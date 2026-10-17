import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from '@app/app.routes';
import { categoryFixture } from '@app/categories/category-fixtures';

describe('CategoryBrowser', () => {
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)],
    });
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('offers an honest empty directory without invented listing counts', async () => {
    const harness = await RouterTestingHarness.create('/categories');
    http.expectOne('/api/v1/categories/').flush([]);
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('No categories available yet');
  });

  it('warns before changing a category with entered attribute values', async () => {
    const second = {
      ...categoryFixture,
      id: '33333333-3333-4333-8333-333333333333',
      name: 'Books',
      slug: 'books',
    };
    const harness = await RouterTestingHarness.create(`/categories/${categoryFixture.id}`);
    http.expectOne('/api/v1/categories/').flush([categoryFixture, second]);
    http.expectOne(`/api/v1/categories/${categoryFixture.id}/`).flush(categoryFixture);
    http
      .expectOne(`/api/v1/categories/${categoryFixture.id}/facets/`)
      .flush({ category_id: categoryFixture.id, version: 2, fields: [] });
    harness.detectChanges();
    http
      .expectOne(
        (request) =>
          request.url === '/api/v1/listings/' &&
          request.params.get('category') === categoryFixture.id,
      )
      .flush({ results: [], count: 0, next: null, previous: null });
    harness.detectChanges();
    const input = harness.routeNativeElement!.querySelector<HTMLInputElement>('input')!;
    input.value = '128';
    input.dispatchEvent(new Event('input'));
    const categoryButton = [
      ...harness.routeNativeElement!.querySelectorAll<HTMLButtonElement>('aside button'),
    ].find((button) => button.textContent?.trim() === 'Books')!;
    categoryButton.click();
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('clear the attribute values');
    http.expectNone(`/api/v1/categories/${second.id}/`);
    const keep = [
      ...harness.routeNativeElement!.querySelectorAll<HTMLButtonElement>('button'),
    ].find((button) => button.textContent?.trim() === 'Keep editing')!;
    keep.click();
    harness.detectChanges();
    expect(input.value).toBe('128');
    expect(harness.routeNativeElement?.textContent).toContain('No public listings yet');
  });
});
