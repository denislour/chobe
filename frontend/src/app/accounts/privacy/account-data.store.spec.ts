import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { AccountDataStore } from './account-data.store';
import { AuthStore } from '@app/auth/auth.store';

describe('AccountDataStore', () => {
  let store: AccountDataStore;
  let http: HttpTestingController;
  beforeEach(async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    TestBed.configureTestingModule({
      providers: [AccountDataStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(AccountDataStore);
    http = TestBed.inject(HttpTestingController);
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
  });
  afterEach(() => {
    TestBed.resetTestingModule();
    http.verify();
    vi.useRealTimers();
  });

  it('creates one export and polls until ready then stops', () => {
    store.createExport();
    store.createExport();
    http
      .expectOne('/api/v1/me/data-exports/')
      .flush({ job_id: 'job', status: 'queued', created_at: '2026-10-13', expires_at: null });
    vi.advanceTimersByTime(0);
    http.expectOne('/api/v1/me/data-exports/').flush([{ job_id: 'job', status: 'queued' }]);
    expect(store.activeExport()).toBe(true);
    vi.advanceTimersByTime(2000);
    http.expectOne('/api/v1/me/data-exports/').flush([{ job_id: 'job', status: 'ready' }]);
    expect(store.activeExport()).toBe(false);
    vi.advanceTimersByTime(10000);
    http.expectNone('/api/v1/me/data-exports/');
  });

  it('shows the throttle wait and permits status refresh without creating another export', () => {
    store.createExport();
    http
      .expectOne('/api/v1/me/data-exports/')
      .flush(
        { detail: 'Request was throttled.' },
        { status: 429, statusText: 'Too Many Requests', headers: { 'Retry-After': '120' } },
      );
    expect(store.error()).toBe(
      'You have reached the limit of 2 account exports per hour. Try again in 2 minutes.',
    );
    expect(store.pending()).toBe(false);
    store.dismissNotification();
    expect(store.error()).toBe('');
    store.load();
    vi.advanceTimersByTime(0);
    const request = http.expectOne('/api/v1/me/data-exports/');
    expect(request.request.method).toBe('GET');
    request.flush([]);
  });

  it('stops polling on error and supports refreshing', () => {
    store.load();
    vi.advanceTimersByTime(0);
    http
      .expectOne('/api/v1/me/data-exports/')
      .flush(null, { status: 503, statusText: 'Unavailable' });
    expect(store.error()).toContain('Unable');
    vi.advanceTimersByTime(10000);
    http.expectNone('/api/v1/me/data-exports/');
    store.load();
    vi.advanceTimersByTime(0);
    http.expectOne('/api/v1/me/data-exports/').flush([]);
    expect(store.error()).toBe('');
  });
});
