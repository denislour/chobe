import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { shopFixture } from './shop-fixtures';
import { ShopStore } from './shop.store';

describe('ShopStore', () => {
  let store: ShopStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [ShopStore, provideHttpClient(), provideHttpClientTesting()] });
    store = TestBed.inject(ShopStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('keeps loading while a newer query replaces a cancelled request', () => {
    store.load();
    const first = http.expectOne('/api/v1/me/shop/');
    store.load();
    expect(first.cancelled).toBe(true);
    expect(store.loading()).toBe(true);
    http.expectOne('/api/v1/me/shop/').flush(shopFixture);
    expect(store.loading()).toBe(false);
  });

  it('treats no shop as a create state and prevents duplicate submission', () => {
    store.load();
    http.expectOne('/api/v1/me/shop/').flush({}, { status: 404, statusText: 'Not Found' });
    expect(store.loaded()).toBe(true);
    expect(store.error()).toBe('');
    const request = { id: null, body: new FormData() };
    store.save(request);
    store.save(request);
    http.expectOne('/api/v1/shops/').flush(shopFixture);
    expect(store.shop()).toEqual(shopFixture);
    expect(store.notice()).toBe('Shop saved.');
    expect(store.pending()).toBe(false);
  });

  it('preserves saved data after a conflict and permits an explicit reload', () => {
    store.load();
    http.expectOne('/api/v1/me/shop/').flush(shopFixture);
    store.save({ id: shopFixture.id, body: new FormData() });
    http.expectOne(`/api/v1/shops/${shopFixture.id}/`).flush({}, { status: 409, statusText: 'Conflict' });
    expect(store.shop()).toEqual(shopFixture);
    expect(store.error()).toContain('changed');
    expect(store.pending()).toBe(false);
    store.load();
    http.expectOne('/api/v1/me/shop/').flush({ ...shopFixture, version: 2 });
    expect(store.shop()?.version).toBe(2);
  });

  it('allows retry after a status error and removes private data on forbidden reload', () => {
    store.load();
    http.expectOne('/api/v1/me/shop/').flush(shopFixture);
    const change = { id: shopFixture.id, status: 'paused' as const, version: 1 };
    store.changeStatus(change);
    http.expectOne(`/api/v1/shops/${shopFixture.id}/status/`).flush({}, { status: 503, statusText: 'Unavailable' });
    expect(store.pending()).toBe(false);
    store.changeStatus(change);
    http.expectOne(`/api/v1/shops/${shopFixture.id}/status/`).flush({ ...shopFixture, status: 'paused', version: 2 });
    expect(store.shop()?.status).toBe('paused');
    store.load();
    http.expectOne('/api/v1/me/shop/').flush({}, { status: 403, statusText: 'Forbidden' });
    expect(store.shop()).toBeNull();
    expect(store.loaded()).toBe(false);
  });
});
