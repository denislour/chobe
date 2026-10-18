import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from '@app/app.routes';
import { AuthStore } from '@app/auth/auth.store';
import { storefrontFixture } from '@app/domain/shop/shop-fixtures';

describe('FollowedShops', () => {
  let http: HttpTestingController;
  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)],
    });
    http = TestBed.inject(HttpTestingController);
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
  });
  afterEach(() => http.verify());

  it('links to the public shop and shows an empty state after unfollowing', async () => {
    const harness = await RouterTestingHarness.create('/account/followed-shops');
    http.expectOne('/api/v1/me/followed-shops/?page=1').flush({
      count: 1, next: null, previous: null, results: [storefrontFixture],
    });
    harness.detectChanges();
    expect(harness.routeNativeElement?.querySelector('main a')?.getAttribute('href'))
      .toBe('/shops/moc-home');
    harness.routeNativeElement!.querySelector<HTMLButtonElement>('li button')!.click();
    http.expectOne(`/api/v1/me/followed-shops/${storefrontFixture.id}/`).flush(null);
    http.expectOne('/api/v1/me/followed-shops/?page=1').flush({
      count: 0, next: null, previous: null, results: [],
    });
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('No shops to show yet');
  });
});
