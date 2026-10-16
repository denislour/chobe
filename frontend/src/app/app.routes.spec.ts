import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
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

  it('requires authentication for shop management', async () => {
    const harness = await RouterTestingHarness.create('/seller/shop');
    const router = TestBed.inject(Router);
    expect(router.parseUrl(router.url).queryParams['returnUrl']).toBe('/seller/shop');
  });
});
