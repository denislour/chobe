import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { storefrontFixture } from '@app/domain/shop/shop-fixtures';
import { FollowedShopsStore } from './followed-shops.store';

describe('FollowedShopsStore', () => {
  let store: FollowedShopsStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [FollowedShopsStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(FollowedShopsStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('returns to the previous page after removing the last item on a page', () => {
    store.load({ page: 2, viewerId: 1 });
    http.expectOne('/api/v1/me/followed-shops/?page=2').flush({
      results: [storefrontFixture], count: 21, next: null, previous: 'page-1',
    });
    store.unfollow(storefrontFixture.id);
    store.unfollow(storefrontFixture.id);
    http.expectOne(`/api/v1/me/followed-shops/${storefrontFixture.id}/`).flush(null);
    expect(store.loading()).toBe(true);
    http.expectOne('/api/v1/me/followed-shops/?page=1').flush({
      results: [], count: 0, next: null, previous: null,
    });
    expect(store.page()).toBe(1);
    expect(store.pending()).toBe(false);
  });

  it('keeps the list after a failed unfollow and allows retry', () => {
    store.load({ page: 1, viewerId: 1 });
    http.expectOne('/api/v1/me/followed-shops/?page=1').flush({
      results: [storefrontFixture], count: 1, next: null, previous: null,
    });
    store.unfollow(storefrontFixture.id);
    http.expectOne(`/api/v1/me/followed-shops/${storefrontFixture.id}/`).flush({}, {
      status: 503, statusText: 'Unavailable',
    });
    expect(store.shops()).toEqual([storefrontFixture]);
    expect(store.pending()).toBe(false);
    store.unfollow(storefrontFixture.id);
    http.expectOne(`/api/v1/me/followed-shops/${storefrontFixture.id}/`).flush(null);
    http.expectOne('/api/v1/me/followed-shops/?page=1').flush({
      results: [], count: 0, next: null, previous: null,
    });
    expect(store.error()).toBe('');
    expect(store.shops()).toEqual([]);
  });

  it('clears private data and cancels the pending query when the viewer logs out', () => {
    store.load({ page: 1, viewerId: 1 });
    const pending = http.expectOne('/api/v1/me/followed-shops/?page=1');
    store.load({ page: 1, viewerId: null });
    expect(pending.cancelled).toBe(true);
    expect(store.shops()).toEqual([]);
    expect(store.loading()).toBe(false);
  });
});
