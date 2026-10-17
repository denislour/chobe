import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { storefrontFixture } from '@app/shops/shop-fixtures';
import { routes } from './app.routes';

describe('Module routes', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)],
    });
  });
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('loads auth pages through the module without changing public URLs', async () => {
    const harness = await RouterTestingHarness.create('/login');
    expect(TestBed.inject(Router).url).toBe('/login');
    expect(harness.routeNativeElement?.querySelector('form')).not.toBeNull();
    await harness.navigateByUrl('/register');
    expect(TestBed.inject(Router).url).toBe('/register');
    expect(harness.routeNativeElement?.querySelector('form')).not.toBeNull();
  });

  it('redirects anonymous users from account pages through the auth guard', async () => {
    await RouterTestingHarness.create('/account/profile');
    const router = TestBed.inject(Router);
    expect(router.url).toContain('/login?');
    expect(router.parseUrl(router.url).queryParams['returnUrl']).toBe('/account/profile');
  });

  it('requires authentication for shop management and preview', async () => {
    const harness = await RouterTestingHarness.create('/seller/shop');
    const router = TestBed.inject(Router);
    expect(router.parseUrl(router.url).queryParams['returnUrl']).toBe('/seller/shop');
    await harness.navigateByUrl('/seller/shop/preview/moc-home');
    expect(router.parseUrl(router.url).queryParams['returnUrl']).toBe(
      '/seller/shop/preview/moc-home',
    );
  });

  it('allows public storefronts while guarding the followed shops page', async () => {
    const harness = await RouterTestingHarness.create('/shops/moc-home');
    TestBed.inject(HttpTestingController)
      .expectOne('/api/v1/shop-storefronts/moc-home/')
      .flush(storefrontFixture);
    harness.detectChanges();
    TestBed.inject(HttpTestingController)
      .expectOne((request) => request.url === '/api/v1/listings/')
      .flush({ results: [], count: 0, next: null, previous: null });
    const router = TestBed.inject(Router);
    expect(router.url).toBe('/shops/moc-home');
    await harness.navigateByUrl('/account/followed-shops');
    expect(router.parseUrl(router.url).queryParams['returnUrl']).toBe('/account/followed-shops');
  });
});
