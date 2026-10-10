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

  it('gets CSRF before posting credentials and returns the user', () => {
    let username = '';
    TestBed.inject(LoginApi)
      .login(credentials)
      .subscribe((user) => (username = user.username));
    http.expectNone('/api/v1/auth/login/');
    const csrf = http.expectOne('/api/v1/auth/csrf/');
    expect(csrf.request.method).toBe('GET');
    csrf.flush(null, { status: 204, statusText: 'No Content' });
    const login = http.expectOne('/api/v1/auth/login/');
    expect(login.request.method).toBe('POST');
    expect(login.request.body).toEqual(credentials);
    login.flush({ id: 1, username: 'admin' });
    expect(username).toBe('admin');
  });

  it('does not send credentials if CSRF setup fails', () => {
    let status = 0;
    TestBed.inject(LoginApi)
      .login(credentials)
      .subscribe({ error: (error) => (status = error.status) });
    http.expectOne('/api/v1/auth/csrf/').flush(null, { status: 503, statusText: 'Unavailable' });
    http.expectNone('/api/v1/auth/login/');
    expect(status).toBe(503);
  });

  it('sends the CSRF cookie in the login header', () => {
    document.cookie = `XSRF-TOKEN=${'x'.repeat(32)}; path=/`;
    TestBed.inject(LoginApi).login(credentials).subscribe();
    http.expectOne('/api/v1/auth/csrf/').flush(null, { status: 204, statusText: 'No Content' });
    const login = http.expectOne('/api/v1/auth/login/');
    expect(login.request.headers.get('X-XSRF-TOKEN')).toBe('x'.repeat(32));
    login.flush({ id: 1, username: 'admin' });
  });
});
