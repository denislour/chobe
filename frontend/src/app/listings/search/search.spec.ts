import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from '@app/app.routes';
import { categoryFixture } from '@app/domain/category/category-fixtures';

describe('Marketplace search', () => {
  it('restores URL filters and keeps the query when clearing filters', async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)],
    });
    const http = TestBed.inject(HttpTestingController);
    const harness = await RouterTestingHarness.create(
      `/search?q=phone&category=${categoryFixture.id}&price_min=1000`,
    );
    http.expectOne('/api/v1/categories/').flush([categoryFixture]);
    const request = http.expectOne((request) => request.url === '/api/v1/listings/');
    expect(request.request.params.get('q')).toBe('phone');
    expect(request.request.params.get('price_min')).toBe('1000');
    request.flush({ results: [], count: 0 });
    harness.detectChanges();
    expect(harness.routeNativeElement!.querySelector<HTMLInputElement>('#price-min')!.value).toBe(
      '1000',
    );
    const clear = [...harness.routeNativeElement!.querySelectorAll('button')].find(
      (button) => button.textContent?.trim() === 'Clear filters',
    )!;
    clear.click();
    await harness.fixture.whenStable();
    const next = http.expectOne((request) => request.url === '/api/v1/listings/');
    expect(next.request.params.has('category')).toBe(false);
    expect(next.request.params.get('q')).toBe('phone');
    next.flush({ results: [], count: 0 });
    expect(TestBed.inject(Router).url).toBe('/search?q=phone');
    http.verify();
  });
});
