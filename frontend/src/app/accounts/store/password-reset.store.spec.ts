import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { PasswordResetStore } from './password-reset.store';
import { AuthStore } from './auth.store';

describe('PasswordResetStore', () => {
  let store: PasswordResetStore;
  let http: HttpTestingController;
  const credentials = {
    uid: 'MQ',
    token: 'token',
    password: 'new-password',
    password_confirm: 'new-password',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [PasswordResetStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(PasswordResetStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('queues one request and finishes with the same success state for any email', () => {
    store.forgotPassword('unknown@example.com');
    store.forgotPassword('unknown@example.com');
    store.resetPassword(credentials);
    expect(store.pending()).toBe(true);
    const request = http.expectOne('/api/v1/auth/forgot-password/');
    expect(request.request.body).toEqual({ email: 'unknown@example.com' });
    request.flush(null, { status: 202, statusText: 'Accepted' });
    expect(store.pending()).toBe(false);
    expect(store.completed()).toBe(true);
    http.expectNone('/api/v1/auth/reset-password/');
  });

  it('clears the current user only after a successful password reset', async () => {
    const auth = TestBed.inject(AuthStore);
    const restoration = auth.restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
    store.resetPassword(credentials);
    const request = http.expectOne('/api/v1/auth/reset-password/');
    expect(request.request.body).toEqual(credentials);
    expect(auth.user()).not.toBeNull();
    request.flush(null, { status: 204, statusText: 'No Content' });
    expect(auth.user()).toBeNull();
    expect(store.completed()).toBe(true);
    expect(store.pending()).toBe(false);
  });

  for (const [status, message] of [
    [400, 'Invalid link'],
    [403, 'security check'],
    [429, 'Too many attempts'],
    [503, 'Unable to connect'],
  ] as const) {
    it(`handles ${status} without automatic retries and supports another attempt`, () => {
      store.resetPassword(credentials);
      http
        .expectOne('/api/v1/auth/reset-password/')
        .flush({ non_field_errors: ['Invalid link'] }, { status, statusText: 'Error' });
      expect(store.error()).toContain(message);
      expect(store.pending()).toBe(false);
      expect(store.completed()).toBe(false);
      store.resetPassword(credentials);
      expect(store.error()).toBe('');
      expect(store.fieldErrors()).toEqual({});
      http
        .expectOne('/api/v1/auth/reset-password/')
        .flush(null, { status: 204, statusText: 'No Content' });
      expect(store.completed()).toBe(true);
    });
  }
});
