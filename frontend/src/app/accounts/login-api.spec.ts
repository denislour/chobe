import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { LoginApi } from './login-api';

describe('LoginApi', () => {
  let http: HttpTestingController;
  const credentials = { username: 'admin', password: 'demo-password' };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    document.cookie = 'XSRF-TOKEN=; Max-Age=0; path=/';
    http.verify();
  });

  it('posts credentials directly and returns the user', () => {
    let username = '';
    TestBed.inject(LoginApi)
      .login(credentials)
      .subscribe((user) => (username = user.username));
    http.expectNone('/api/v1/auth/csrf/');
    const login = http.expectOne('/api/v1/auth/login/');
    expect(login.request.method).toBe('POST');
    expect(login.request.body).toEqual(credentials);
    login.flush({ id: 1, username: 'admin' });
    expect(username).toBe('admin');
  });

  it('gets session without sending a CSRF header', () => {
    TestBed.inject(LoginApi).session().subscribe();
    const request = http.expectOne('/api/v1/auth/session/');
    expect(request.request.method).toBe('GET');
    expect(request.request.headers.has('X-XSRF-TOKEN')).toBe(false);
    request.flush({ user: null });
  });

  it('posts the reset token and new password without fetching CSRF again', () => {
    document.cookie = `XSRF-TOKEN=${'x'.repeat(32)}; path=/`;
    const reset = {
      uid: 'MQ',
      token: 'token',
      password: 'new-safe-password',
      password_confirm: 'new-safe-password',
    };
    TestBed.inject(LoginApi).resetPassword(reset).subscribe();
    const request = http.expectOne('/api/v1/auth/reset-password/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(reset);
    expect(request.request.headers.get('X-XSRF-TOKEN')).toBe('x'.repeat(32));
    http.expectNone('/api/v1/auth/csrf/');
    request.flush(null, { status: 204, statusText: 'No Content' });
  });

  it('registers with the CSRF header and returns the new user', () => {
    document.cookie = `XSRF-TOKEN=${'x'.repeat(32)}; path=/`;
    const registration = { ...credentials, email: 'admin@example.com', accept_terms: true };
    let userId = 0;
    TestBed.inject(LoginApi)
      .register(registration)
      .subscribe((user) => (userId = user.id));
    const request = http.expectOne('/api/v1/auth/register/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(registration);
    expect(request.request.headers.get('X-XSRF-TOKEN')).toBe('x'.repeat(32));
    request.flush({ id: 2, username: 'admin' }, { status: 201, statusText: 'Created' });
    expect(userId).toBe(2);
    http.expectNone('/api/v1/auth/csrf/');
  });

  it('sends the CSRF cookie in the login header', () => {
    document.cookie = `XSRF-TOKEN=${'x'.repeat(32)}; path=/`;
    TestBed.inject(LoginApi).login(credentials).subscribe();
    const login = http.expectOne('/api/v1/auth/login/');
    expect(login.request.headers.get('X-XSRF-TOKEN')).toBe('x'.repeat(32));
    login.flush({ id: 1, username: 'admin' });
  });

  it('reads the rotated cookie for logout without fetching CSRF again', () => {
    const api = TestBed.inject(LoginApi);
    document.cookie = `XSRF-TOKEN=${'x'.repeat(32)}; path=/`;
    api.login(credentials).subscribe();
    http.expectOne('/api/v1/auth/login/').flush({ id: 1, username: 'admin' });
    document.cookie = `XSRF-TOKEN=${'y'.repeat(32)}; path=/`;
    api.logout().subscribe();
    const request = http.expectOne('/api/v1/auth/logout/');
    expect(request.request.method).toBe('POST');
    expect(request.request.headers.get('X-XSRF-TOKEN')).toBe('y'.repeat(32));
    http.expectNone('/api/v1/auth/csrf/');
    request.flush(null, { status: 204, statusText: 'No Content' });
  });
});
