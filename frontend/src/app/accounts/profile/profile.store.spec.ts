import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { profileFixture } from '@app/accounts/account-fixtures';
import { ProfileStore } from './profile.store';

describe('ProfileStore', () => {
  let store: ProfileStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ProfileStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(ProfileStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('loads and saves once while exposing the updated version', () => {
    store.load();
    expect(store.loading()).toBe(true);
    http.expectOne('/api/v1/me/profile/').flush(profileFixture);
    const body = new FormData();
    body.set('version', '1');
    store.save(body);
    store.save(body);
    const request = http.expectOne('/api/v1/me/profile/');
    expect(store.pending()).toBe(true);
    request.flush({ ...profileFixture, version: 2 });
    expect(store.profile()?.version).toBe(2);
    expect(store.saved()).toBe(true);
    expect(store.pending()).toBe(false);
  });

  for (const [status, message] of [
    [400, 'Invalid phone.'],
    [403, 'security'],
    [409, 'changed'],
    [503, 'Unable'],
  ] as const) {
    it(`preserves data and supports retry after ${status}`, () => {
      store.load();
      http.expectOne('/api/v1/me/profile/').flush(profileFixture);
      store.save(new FormData());
      http
        .expectOne('/api/v1/me/profile/')
        .flush({ phone: ['Invalid phone.'] }, { status, statusText: 'Error' });
      expect(store.error()).toContain(message);
      expect(store.pending()).toBe(false);
      expect(store.profile()).toEqual(profileFixture);
      store.save(new FormData());
      http.expectOne('/api/v1/me/profile/').flush({ ...profileFixture, version: 2 });
      expect(store.error()).toBe('');
    });
  }
});
