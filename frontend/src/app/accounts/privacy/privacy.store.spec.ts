import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { privacyFixture } from '@app/accounts/account-fixtures';
import { PrivacyStore } from './privacy.store';

describe('PrivacyStore', () => {
  let store: PrivacyStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [PrivacyStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(PrivacyStore);
    http = TestBed.inject(HttpTestingController);
    store.load();
    http.expectOne('/api/v1/me/privacy-settings/').flush(privacyFixture);
    http
      .expectOne('/api/v1/me/viewing-history/')
      .flush([{ listing_id: 1, viewed_at: '2026-10-13T00:00:00Z' }]);
  });
  afterEach(() => http.verify());

  it('opts out once and clears existing history only after success', () => {
    const values = { share_phone: false, record_history: false, version: 1 };
    store.save(values);
    store.save(values);
    expect(store.history()).toHaveLength(1);
    http
      .expectOne('/api/v1/me/privacy-settings/')
      .flush({ ...privacyFixture, ...values, version: 2 });
    expect(store.history()).toEqual([]);
    expect(store.privacy()?.version).toBe(2);
    expect(store.pending()).toBe(false);
  });

  it('reloads current settings after a conflict without resubmitting changes', () => {
    store.save({ share_phone: false, record_history: false, version: 1 });
    http
      .expectOne('/api/v1/me/privacy-settings/')
      .flush({}, { status: 409, statusText: 'Conflict' });
    expect(store.pending()).toBe(true);
    http.expectOne('/api/v1/me/privacy-settings/').flush({ ...privacyFixture, version: 2 });
    http.expectOne('/api/v1/me/viewing-history/').flush([]);
    expect(store.error()).toBe('Your settings changed. Please review and save again.');
    expect(store.privacy()?.version).toBe(2);
    expect(store.history()).toEqual([]);
    expect(store.pending()).toBe(false);
    http.expectNone('/api/v1/me/privacy-settings/');
    expect(store.loading()).toBe(false);
  });

  it('clears history through the API', () => {
    store.clearHistory();
    http
      .expectOne('/api/v1/me/viewing-history/')
      .flush(null, { status: 204, statusText: 'No Content' });
    expect(store.history()).toEqual([]);
    expect(store.notice()).toContain('cleared');
  });
});
