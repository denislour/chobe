import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationInitStatus } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { appConfig } from '../app.config';
import { AuthStore } from './auth.store';

describe('AuthStore', () => {
  let store: AuthStore;
  let http: HttpTestingController;
  const user = { id: 1, username: 'admin' };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(AuthStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  for (const currentUser of [user, null]) {
    it(`restores a ${currentUser ? 'logged-in' : 'guest'} session`, () => {
      void store.restoreSession();
      const request = http.expectOne('/api/v1/auth/session/');
      expect(request.request.method).toBe('GET');
      request.flush({ user: currentUser });
      expect(store.user()).toEqual(currentUser);
      expect(store.sessionError()).toBe('');
    });
  }

  it('allows startup to finish on a session error and supports retry', async () => {
    const restoration = store.restoreSession();
    http.expectOne('/api/v1/auth/session/').flush(null, { status: 503, statusText: 'Unavailable' });
    await restoration;
    expect(store.sessionError()).toContain('Unable to check your session');
    void store.restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user });
    expect(store.user()).toEqual(user);
    expect(store.sessionError()).toBe('');
  });

  it('stores the login response without requesting session again', () => {
    store.login({ username: 'admin', password: 'demo-password' });
    http.expectOne('/api/v1/auth/login/').flush(user);
    expect(store.user()).toEqual(user);
    http.expectNone('/api/v1/auth/session/');
  });

  it('blocks mutations during restoration and login for an authenticated user', async () => {
    const restoration = store.restoreSession();
    const credentials = { username: 'admin', password: 'demo-password' };
    store.login(credentials);
    store.logout();
    http.expectNone('/api/v1/auth/login/');
    http.expectNone('/api/v1/auth/logout/');
    http.expectOne('/api/v1/auth/session/').flush({ user });
    await restoration;
    store.login(credentials);
    http.expectNone('/api/v1/auth/login/');
    expect(store.user()).toEqual(user);
    expect(store.pending()).toBe(false);
  });

  it('blocks overlapping auth operations and accepts login again after an error', async () => {
    const credentials = { username: 'admin', password: 'demo-password' };
    store.login(credentials);
    expect(store.pending()).toBe(true);
    store.login(credentials);
    store.logout();
    await store.restoreSession();
    http.expectNone('/api/v1/auth/logout/');
    http.expectNone('/api/v1/auth/session/');
    http.expectOne('/api/v1/auth/login/').flush(null, { status: 400, statusText: 'Bad Request' });
    expect(store.pending()).toBe(false);
    expect(store.error()).toBe('Invalid username or password.');
    store.login(credentials);
    expect(store.error()).toBe('');
    http.expectOne('/api/v1/auth/login/').flush(user);
    expect(store.pending()).toBe(false);
    expect(store.user()).toEqual(user);
  });

  it('keeps the logout method usable after an error', () => {
    void store.restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user });
    store.logout();
    http.expectOne('/api/v1/auth/logout/').flush(null, { status: 403, statusText: 'Forbidden' });
    expect(store.user()).toEqual(user);
    expect(store.error()).toContain('Reload this page');
    store.logout();
    expect(store.error()).toBe('');
    http.expectOne('/api/v1/auth/logout/').flush(null, { status: 204, statusText: 'No Content' });
    expect(store.user()).toBeNull();
    expect(store.pending()).toBe(false);
  });

  it('finishes restoration when the session request times out', async () => {
    vi.useFakeTimers();
    try {
      const restoration = store.restoreSession();
      const request = http.expectOne('/api/v1/auth/session/');
      await vi.advanceTimersByTimeAsync(5000);
      expect(request.cancelled).toBe(true);
      await restoration;
      expect(store.sessionError()).toContain('Unable to check your session');
    } finally {
      vi.useRealTimers();
    }
  });

  for (const status of [204, 503]) {
    it(`${status === 204 ? 'clears' : 'retains'} the user after logout status ${status}`, () => {
      void store.restoreSession();
      http.expectOne('/api/v1/auth/session/').flush({ user });
      store.logout();
      const request = http.expectOne('/api/v1/auth/logout/');
      expect(request.request.method).toBe('POST');
      request.flush(null, { status, statusText: status === 204 ? 'No Content' : 'Unavailable' });
      expect(store.user()).toEqual(status === 204 ? null : user);
    });
  }
});

describe('Session initialization', () => {
  it('loads the shared user during application startup', async () => {
    TestBed.configureTestingModule({
      providers: [...appConfig.providers, provideHttpClientTesting()],
    });
    const init = TestBed.inject(ApplicationInitStatus);
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'admin' } });
    await init.donePromise;
    expect(TestBed.inject(AuthStore).user()?.username).toBe('admin');
    http.verify();
  });
});
