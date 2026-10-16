import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { shopFixture } from '@app/shops/shop-fixtures';
import { ShopPreviewStore } from './shop-preview.store';

describe('ShopPreviewStore', () => {
  it('does not retain a preview when the next lookup is forbidden', () => {
    TestBed.configureTestingModule({ providers: [ShopPreviewStore, provideHttpClient(), provideHttpClientTesting()] });
    const store = TestBed.inject(ShopPreviewStore);
    const http = TestBed.inject(HttpTestingController);
    store.load('moc-home');
    http.expectOne('/api/v1/shops/moc-home/preview/').flush(shopFixture);
    expect(store.shop()?.slug).toBe('moc-home');
    store.load('other-shop');
    http.expectOne('/api/v1/shops/other-shop/preview/').flush({}, { status: 403, statusText: 'Forbidden' });
    expect(store.shop()).toBeNull();
    expect(store.loading()).toBe(false);
    expect(store.error()).toContain('Log in');
    http.verify();
  });
});
