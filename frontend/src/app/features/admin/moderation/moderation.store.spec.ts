import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { reviewFixture } from '@app/domain/listing/listing-fixtures';
import { ModerationStore } from './moderation.store';
describe('ModerationStore', () => {
  let store: ModerationStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ModerationStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(ModerationStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  function select(): void {
    store.select(7);
    http.expectOne('/api/v1/admin/moderation/7/').flush(reviewFixture);
    http.expectOne('/api/v1/admin/moderation/7/history/').flush([]);
  }
  it('lets an admin approve a rejected snapshot with a new audited decision', () => {
    store.select(7);
    http.expectOne('/api/v1/admin/moderation/7/').flush({ ...reviewFixture, status: 'rejected' });
    http.expectOne('/api/v1/admin/moderation/7/history/').flush([]);
    store.decide({ decision: 'approve', reason: 'Re-reviewed and accepted.' });
    store.decide({ decision: 'approve', reason: 'Duplicate' });
    const request = http.expectOne('/api/v1/admin/moderation/7/decision/');
    expect(request.request.body).toEqual({
      version: 1,
      decision: 'approve',
      reason: 'Re-reviewed and accepted.',
    });
    request.flush({ ...reviewFixture, status: 'approved', version: 2 });
    http
      .expectOne((request) => request.url === '/api/v1/admin/moderation/')
      .flush({ results: [], count: 0 });
    expect(store.notice()).toContain('published');
  });
  it('keeps the selected snapshot after a conflict so the reason is not lost', () => {
    select();
    store.decide({ decision: 'reject', reason: 'Needs clarification.' });
    http
      .expectOne('/api/v1/admin/moderation/7/decision/')
      .flush({}, { status: 409, statusText: 'Conflict' });
    expect(store.selected()?.id).toBe(7);
    expect(store.pending()).toBe(false);
    expect(store.error()).toContain('Reload');
  });
  it('does not decide on a stale submission', () => {
    store.select(7);
    http.expectOne('/api/v1/admin/moderation/7/').flush({ ...reviewFixture, current: false });
    http.expectOne('/api/v1/admin/moderation/7/history/').flush([]);
    store.decide({ decision: 'approve', reason: 'Stale' });
    http.expectNone('/api/v1/admin/moderation/7/decision/');
  });
});
