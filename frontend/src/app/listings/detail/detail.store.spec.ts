import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { listingFixture } from '@app/domain/listing/listing-fixtures';
import { DetailStore } from './detail.store';
describe('DetailStore', () => {
  let store: DetailStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [DetailStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(DetailStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('does not write history for a guest', () => {
    store.load({ id: 12, record: false });
    http.expectOne('/api/v1/listings/12/').flush(listingFixture);
    http.expectNone('/api/v1/me/viewing-history/');
    expect(store.listing()?.phone).toBe(listingFixture.phone);
  });
  it('retains the listing when recording history fails and can retry', () => {
    store.load({ id: 12, record: true });
    http.expectOne('/api/v1/listings/12/').flush(listingFixture);
    http
      .expectOne('/api/v1/me/viewing-history/')
      .flush({}, { status: 503, statusText: 'Unavailable' });
    expect(store.listing()?.id).toBe(12);
    expect(store.historyError()).toContain('could not');
    store.recordHistory(12);
    http
      .expectOne('/api/v1/me/viewing-history/')
      .flush(null, { status: 204, statusText: 'No Content' });
    expect(store.historyError()).toBe('');
  });
  it('changes the saved state only after success and blocks duplicate mutations', () => {
    store.load({ id: 12, record: false });
    http.expectOne('/api/v1/listings/12/').flush(listingFixture);
    store.favorite();
    store.favorite();
    http
      .expectOne('/api/v1/me/favorites/12/')
      .flush(null, { status: 204, statusText: 'No Content' });
    expect(store.listing()?.is_favorite).toBe(true);
    expect(store.pending()).toBe(false);
  });
});
