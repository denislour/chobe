import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ProfileApi } from './profile-api';
import { profileFixture } from '@app/accounts/account-fixtures';

describe('ProfileApi', () => {
  let api: ProfileApi;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(ProfileApi);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    document.cookie = 'XSRF-TOKEN=; Max-Age=0; path=/';
    http.verify();
  });

  it('reads the private profile endpoint', () => {
    api.profile().subscribe();
    http.expectOne('/api/v1/me/profile/').flush(profileFixture);
  });

  it('patches multipart profile with CSRF and lets the browser set the content type', () => {
    document.cookie = `XSRF-TOKEN=${'x'.repeat(32)}; path=/`;
    const body = new FormData();
    body.set('version', '1');
    body.set('display_name', 'Member');
    api.saveProfile(body).subscribe();
    const request = http.expectOne('/api/v1/me/profile/');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toBe(body);
    expect(request.request.headers.has('Content-Type')).toBe(false);
    expect(request.request.headers.get('X-XSRF-TOKEN')).toBe('x'.repeat(32));
    request.flush(profileFixture);
  });
});
