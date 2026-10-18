import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ShopApi } from './shop-api';
import { shopFixture } from '@app/domain/shop/shop-fixtures';

describe('ShopApi', () => {
  let api: ShopApi;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(ShopApi);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    document.cookie = 'XSRF-TOKEN=; Max-Age=0; path=/';
    http.verify();
  });

  it('creates and updates multipart shop details with CSRF', () => {
    document.cookie = `XSRF-TOKEN=${'x'.repeat(32)}; path=/`;
    const body = new FormData();
    body.set('name', 'Moc Home');
    api.save({ id: null, body }).subscribe();
    const create = http.expectOne('/api/v1/shops/');
    expect(create.request.method).toBe('POST');
    expect(create.request.headers.get('X-XSRF-TOKEN')).toBe('x'.repeat(32));
    expect(create.request.headers.has('Content-Type')).toBe(false);
    create.flush(shopFixture);
    body.set('version', '1');
    api.save({ id: shopFixture.id, body }).subscribe();
    const update = http.expectOne(`/api/v1/shops/${shopFixture.id}/`);
    expect(update.request.method).toBe('PATCH');
    expect(update.request.body).toBe(body);
    update.flush({ ...shopFixture, version: 2 });
  });

  it('reads owner data and sends versioned status changes', () => {
    api.mine().subscribe();
    http.expectOne('/api/v1/shops/mine/').flush(shopFixture);
    api.preview('moc-home').subscribe();
    http.expectOne('/api/v1/shops/moc-home/preview/').flush(shopFixture);
    api.changeStatus({ id: shopFixture.id, status: 'paused', version: 1 }).subscribe();
    const request = http.expectOne(`/api/v1/shops/${shopFixture.id}/status/`);
    expect(request.request.body).toEqual({ status: 'paused', version: 1 });
    request.flush({ ...shopFixture, status: 'paused', version: 2 });
  });
});
