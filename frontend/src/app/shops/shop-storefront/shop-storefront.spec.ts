import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from '@app/app.routes';
import { AuthStore } from '@app/auth/auth.store';
import { storefrontFixture } from '@app/shops/shop-fixtures';

describe('ShopStorefront', () => {
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)],
    });
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('shows a public shop to guests and returns to the same page after login', async () => {
    const harness = await RouterTestingHarness.create('/shops/moc-home?tab=about');
    http.expectOne('/api/v1/shop-storefronts/moc-home/').flush(storefrontFixture);
    harness.detectChanges();
    http
      .match((request) => request.url === '/api/v1/listings/')
      .forEach((request) => request.flush({ results: [], count: 0, next: null, previous: null }));
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('About Moc Home');
    const button = harness.routeNativeElement!.querySelector<HTMLButtonElement>('.follow-button')!;
    button.click();
    await harness.fixture.whenStable();
    const router = TestBed.inject(Router);
    expect(router.parseUrl(router.url).queryParams['returnUrl']).toBe('/shops/moc-home?tab=about');
    http.expectNone(`/api/v1/me/followed-shops/${storefrontFixture.id}/`);
  });

  it('reloads the storefront when the slug changes on the same component', async () => {
    const harness = await RouterTestingHarness.create('/shops/moc-home');
    http.expectOne('/api/v1/shop-storefronts/moc-home/').flush(storefrontFixture);
    harness.detectChanges();
    http
      .match((request) => request.url === '/api/v1/listings/')
      .forEach((request) => request.flush({ results: [], count: 0, next: null, previous: null }));
    harness.detectChanges();
    await harness.navigateByUrl('/shops/another-shop');
    http.expectOne('/api/v1/shop-storefronts/another-shop/').flush({
      ...storefrontFixture,
      id: 'another-id',
      name: 'Another shop',
      slug: 'another-shop',
    });
    harness.detectChanges();
    http
      .match((request) => request.url === '/api/v1/listings/')
      .forEach((request) => request.flush({ results: [], count: 0, next: null, previous: null }));
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('Another shop');
    expect(harness.routeNativeElement?.textContent).toContain('No public listings yet');
  });

  it('updates the follow button only after the authenticated request succeeds', async () => {
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
    const harness = await RouterTestingHarness.create('/shops/moc-home');
    http.expectOne('/api/v1/shop-storefronts/moc-home/').flush(storefrontFixture);
    harness.detectChanges();
    http
      .match((request) => request.url === '/api/v1/listings/')
      .forEach((request) => request.flush({ results: [], count: 0, next: null, previous: null }));
    harness.detectChanges();
    const button = harness.routeNativeElement!.querySelector<HTMLButtonElement>('.follow-button')!;
    button.click();
    harness.detectChanges();
    http
      .match((request) => request.url === '/api/v1/listings/')
      .forEach((request) => request.flush({ results: [], count: 0, next: null, previous: null }));
    harness.detectChanges();
    expect(button.disabled).toBe(true);
    const request = http.expectOne(`/api/v1/me/followed-shops/${storefrontFixture.id}/`);
    expect(request.request.method).toBe('PUT');
    request.flush(null, { status: 204, statusText: 'No Content' });
    harness.detectChanges();
    http
      .match((request) => request.url === '/api/v1/listings/')
      .forEach((request) => request.flush({ results: [], count: 0, next: null, previous: null }));
    harness.detectChanges();
    expect(button.getAttribute('aria-pressed')).toBe('true');
    expect(button.disabled).toBe(false);
  });

  it('removes unavailable shop content and offers retry', async () => {
    const harness = await RouterTestingHarness.create('/shops/missing');
    http.expectOne('/api/v1/shop-storefronts/missing/').flush(
      {},
      {
        status: 404,
        statusText: 'Not Found',
      },
    );
    harness.detectChanges();
    http
      .match((request) => request.url === '/api/v1/listings/')
      .forEach((request) => request.flush({ results: [], count: 0, next: null, previous: null }));
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('not available');
    expect(harness.routeNativeElement?.querySelector('.follow-button')).toBeNull();
    harness.routeNativeElement!.querySelector<HTMLButtonElement>('main button')!.click();
    http
      .expectOne('/api/v1/shop-storefronts/missing/')
      .flush({ ...storefrontFixture, slug: 'missing' });
    harness.detectChanges();
    http
      .match((request) => request.url === '/api/v1/listings/')
      .forEach((request) => request.flush({ results: [], count: 0, next: null, previous: null }));
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('Moc Home');
  });
});
