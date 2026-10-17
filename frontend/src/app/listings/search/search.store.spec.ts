import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { listingFixture } from '@app/listings/listing-fixtures';
import { SearchStore } from './search.store';
describe('SearchStore', () => {
  let store: SearchStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [SearchStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(SearchStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('uses URL filters and cancels an older query', () => {
    store.load({ q: 'old' });
    const old = http.expectOne((request) => request.params.get('q') === 'old');
    store.load({ q: 'demo', attributes: { tested: false } });
    expect(old.cancelled).toBe(true);
    const request = http.expectOne((request) => request.params.get('q') === 'demo');
    expect(request.request.params.get('attributes')).toBe('{"tested":false}');
    request.flush({ results: [listingFixture], count: 1, next: null, previous: null });
    expect(store.count()).toBe(1);
    expect(store.listings()[0].title).toBe('Demo phone');
    expect(store.loading()).toBe(false);
  });
  it('can retry a failed request and show an empty result', () => {
    store.load({});
    http.expectOne('/api/v1/listings/').flush({}, { status: 503, statusText: 'Unavailable' });
    expect(store.error()).toContain('try again');
    store.load({});
    http
      .expectOne('/api/v1/listings/')
      .flush({ results: [], count: 0, next: null, previous: null });
    expect(store.error()).toBe('');
    expect(store.listings()).toEqual([]);
  });
});
