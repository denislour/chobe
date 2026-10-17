import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { AlertsStore } from './alerts.store';
describe('AlertsStore', () => {
  let store: AlertsStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AlertsStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(AlertsStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  function load(): void {
    store.load(1);
    http.expectOne('/api/v1/me/saved-searches/?page=1').flush({ results: [], count: 0 });
    http.expectOne('/api/v1/me/notifications/?page=1').flush({ results: [], count: 0 });
    http
      .expectOne('/api/v1/me/notification-preferences/me/')
      .flush({ inbox: false, email: false, version: 1 });
  }
  it('saves a search once and shows recovery after a conflict', () => {
    const values = {
      name: 'Phones',
      filters: { q: 'phone' },
      active: true,
      frequency: 'daily' as const,
    };
    store.save({ id: null, values });
    store.save({ id: null, values });
    const request = http.expectOne('/api/v1/me/saved-searches/');
    expect(request.request.body).toEqual(values);
    request.flush({ id: 3, ...values, version: 1 });
    expect(store.notice()).toContain('Search saved');
    expect(store.pending()).toBe(false);
    store.save({ id: 3, values: { ...values, version: 1 } });
    http
      .expectOne('/api/v1/me/saved-searches/3/')
      .flush({}, { status: 409, statusText: 'Conflict' });
    expect(store.error()).toContain('Reload');
  });
  it('loads preferences without treating them as consent until explicitly saved', () => {
    load();
    expect(store.preferences()?.email).toBe(false);
    store.change({ kind: 'preferences', values: { inbox: true, email: true, version: 1 } });
    const request = http.expectOne('/api/v1/me/notification-preferences/me/');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body.version).toBe(1);
    request.flush({}, { status: 503, statusText: 'Unavailable' });
    expect(store.preferences()?.email).toBe(false);
    expect(store.pending()).toBe(false);
  });
});
