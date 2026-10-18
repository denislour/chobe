import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { storefrontFixture } from '@app/domain/shop/shop-fixtures';
import { StorefrontStore } from './storefront.store';

const url = '/api/v1/shop-storefronts/moc-home/';
const followUrl = `/api/v1/me/followed-shops/${storefrontFixture.id}/`;
const change = { shopId: storefrontFixture.id, viewerId: 1, following: true };

describe('StorefrontStore', () => {
  let store: StorefrontStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [StorefrontStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(StorefrontStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('cancels the old shop query and keeps the newer query loading', () => {
    store.load({ slug: 'moc-home', viewerId: null });
    const old = http.expectOne(url);
    store.load({ slug: 'moc-living', viewerId: null });
    expect(old.cancelled).toBe(true);
    expect(store.loading()).toBe(true);
    http.expectOne('/api/v1/shop-storefronts/moc-living/').flush({ ...storefrontFixture, slug: 'moc-living' });
    expect(store.shop()?.slug).toBe('moc-living');
    expect(store.loading()).toBe(false);
  });

  it('keeps the old follow state on failure and permits a retry without duplicate writes', () => {
    store.load({ slug: 'moc-home', viewerId: 1 });
    http.expectOne(url).flush(storefrontFixture);
    store.changeFollowing(change);
    store.changeFollowing(change);
    http.expectOne(followUrl).flush({}, { status: 503, statusText: 'Unavailable' });
    expect(store.shop()?.is_following).toBe(false);
    expect(store.pending()).toBe(false);
    expect(store.followError()).toContain('try again');
    store.changeFollowing(change);
    http.expectOne(followUrl).flush(null, { status: 204, statusText: 'No Content' });
    expect(store.shop()?.is_following).toBe(true);
    expect(store.followError()).toBe('');
  });

  it('does not apply a late follow response to a different viewer', () => {
    store.load({ slug: 'moc-home', viewerId: 1 });
    http.expectOne(url).flush(storefrontFixture);
    store.changeFollowing(change);
    const pending = http.expectOne(followUrl);
    store.load({ slug: 'moc-home', viewerId: 2 });
    http.expectOne(url).flush(storefrontFixture);
    pending.flush(null, { status: 204, statusText: 'No Content' });
    expect(store.shop()?.is_following).toBe(false);
    expect(store.notice()).toBe('');
  });

  it('removes the displayed shop when it becomes unavailable during follow', () => {
    store.load({ slug: 'moc-home', viewerId: 1 });
    http.expectOne(url).flush(storefrontFixture);
    store.changeFollowing(change);
    http.expectOne(followUrl).flush({}, { status: 404, statusText: 'Not Found' });
    expect(store.shop()).toBeNull();
    expect(store.error()).toContain('not available');
    expect(store.pending()).toBe(false);
  });
});
