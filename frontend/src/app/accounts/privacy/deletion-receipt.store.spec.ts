import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { DeletionReceiptStore } from './deletion-receipt.store';

describe('DeletionReceiptStore', () => {
  let store: DeletionReceiptStore;
  let http: HttpTestingController;
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    TestBed.configureTestingModule({
      providers: [DeletionReceiptStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(DeletionReceiptStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    TestBed.resetTestingModule();
    http.verify();
    vi.useRealTimers();
  });

  it('polls a receipt until completion without restoring a user', () => {
    store.load('receipt');
    vi.advanceTimersByTime(0);
    http
      .expectOne('/api/v1/account-deletion-status/receipt/')
      .flush({ job_id: 'job', status: 'requested' });
    vi.advanceTimersByTime(2000);
    http
      .expectOne('/api/v1/account-deletion-status/receipt/')
      .flush({ job_id: 'job', status: 'completed' });
    expect(store.job()?.status).toBe('completed');
    vi.advanceTimersByTime(10000);
    http.expectNone('/api/v1/account-deletion-status/receipt/');
  });

  it('stops on an invalid receipt and exposes an error', () => {
    store.load('invalid');
    vi.advanceTimersByTime(0);
    http
      .expectOne('/api/v1/account-deletion-status/invalid/')
      .flush({}, { status: 404, statusText: 'Not Found' });
    expect(store.error()).toContain('expired');
    expect(store.loading()).toBe(false);
    vi.advanceTimersByTime(10000);
    http.expectNone('/api/v1/account-deletion-status/invalid/');
  });
});
