import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { DeletionReceipt } from './deletion-receipt';

describe('DeletionReceipt', () => {
  it('shows completion without exposing account identity', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    try {
      TestBed.configureTestingModule({
        imports: [DeletionReceipt],
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          provideRouter([]),
          {
            provide: ActivatedRoute,
            useValue: { snapshot: { paramMap: convertToParamMap({ receipt: 'receipt' }) } },
          },
        ],
      });
      const http = TestBed.inject(HttpTestingController);
      const fixture = TestBed.createComponent(DeletionReceipt);
      fixture.detectChanges();
      vi.advanceTimersByTime(0);
      http
        .expectOne('/api/v1/account-deletion-status/receipt/')
        .flush({ job_id: 'job', status: 'completed' });
      await fixture.whenStable();
      expect(fixture.nativeElement.textContent).toContain('account data have been removed');
      http.verify();
    } finally {
      TestBed.resetTestingModule();
      vi.useRealTimers();
    }
  });
});
