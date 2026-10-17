import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ReportsStore } from './reports.store';
import { ReportRecord } from './reports-api';
const report: ReportRecord = {
  id: '11111111-1111-4111-8111-111111111111',
  listing: 12,
  shop: null,
  reason: 'incorrect',
  description: 'Needs investigation',
  status: 'open',
  response: '',
  version: 1,
  created_at: '2026-10-17T00:00:00Z',
};
describe('ReportsStore', () => {
  let store: ReportsStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ReportsStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(ReportsStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('uses the private reporter endpoint and preserves selection during an action conflict', () => {
    store.load({ admin: false, page: 1, status: '' });
    http
      .expectOne((request) => request.url === '/api/v1/me/reports/')
      .flush({ results: [report], count: 1 });
    store.select(report, false);
    expect(store.selected()?.description).toBe('Needs investigation');
    store.decide({
      id: report.id,
      values: { version: 1, action: 'resolve', reason: 'Reviewed', response: 'Resolved' },
    });
    http
      .expectOne(`/api/v1/admin/reports/${report.id}/decision/`)
      .flush({}, { status: 409, statusText: 'Conflict' });
    expect(store.error()).toContain('Reload');
    expect(store.pending()).toBe(false);
    expect(store.selected()?.version).toBe(1);
  });
  it('loads an admin queue with an explicit status filter', () => {
    store.load({ admin: true, page: 1, status: 'open' });
    const request = http.expectOne((request) => request.url === '/api/v1/admin/reports/');
    expect(request.request.params.get('status')).toBe('open');
    request.flush({ results: [], count: 0 });
    expect(store.reports()).toEqual([]);
    expect(store.loading()).toBe(false);
  });
});
