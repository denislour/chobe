import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { draftFixture } from '@app/listings/listing-fixtures';
import { DashboardStore } from './dashboard.store';
describe('DashboardStore', () => {
  it('requires the current version for an owner action and keeps the list after conflict', () => {
    TestBed.configureTestingModule({
      providers: [DashboardStore, provideHttpClient(), provideHttpClientTesting()],
    });
    const store = TestBed.inject(DashboardStore);
    const http = TestBed.inject(HttpTestingController);
    store.load({ state: 'active', q: '', page: 1, retention: '' });
    http
      .expectOne((request) => request.url === '/api/v1/me/listings/')
      .flush({ results: [draftFixture], count: 1 });
    http.expectOne('/api/v1/me/listings/summary/').flush({ active: 1 });
    store.change({ listing: draftFixture, kind: 'renew' });
    store.change({ listing: draftFixture, kind: 'renew' });
    const request = http.expectOne('/api/v1/me/listings/12/renew/');
    expect(request.request.body.version).toBe(4);
    request.flush({}, { status: 409, statusText: 'Conflict' });
    expect(store.listings()[0].id).toBe(12);
    expect(store.pending()).toBe(false);
    expect(store.error()).toContain('Reload');
    http.verify();
  });
});
