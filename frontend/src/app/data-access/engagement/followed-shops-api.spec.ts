import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { FollowedShopsApi } from './followed-shops-api';

describe('FollowedShopsApi', () => {
  let api: FollowedShopsApi;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(FollowedShopsApi);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    document.cookie = 'XSRF-TOKEN=; Max-Age=0; path=/';
    http.verify();
  });

  it('uses same-origin versioned endpoints and CSRF for follow changes', () => {
    document.cookie = `XSRF-TOKEN=${'x'.repeat(32)}; path=/`;
    api.setFollowing('shop-id', true).subscribe();
    const follow = http.expectOne('/api/v1/me/followed-shops/shop-id/');
    expect(follow.request.method).toBe('PUT');
    expect(follow.request.headers.get('X-XSRF-TOKEN')).toBe('x'.repeat(32));
    follow.flush(null);
    api.setFollowing('shop-id', false).subscribe();
    const unfollow = http.expectOne('/api/v1/me/followed-shops/shop-id/');
    expect(unfollow.request.method).toBe('DELETE');
    expect(unfollow.request.headers.get('X-XSRF-TOKEN')).toBe('x'.repeat(32));
    unfollow.flush(null);
  });

  it('requests pagination through the fixed local endpoint', () => {
    api.list(2).subscribe();
    const request = http.expectOne('/api/v1/me/followed-shops/?page=2');
    expect(request.request.method).toBe('GET');
    request.flush({ count: 0, next: null, previous: null, results: [] });
  });
});
