import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthStore } from '@app/auth/auth.store';
import { ReportForm } from './report-form';
describe('ReportForm', () => {
  it('keeps the report text on failure and shows the receipt after retry', async () => {
    await TestBed.configureTestingModule({
      imports: [ReportForm],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthStore, useValue: { user: () => ({ id: 1, username: 'member' }) } },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(ReportForm);
    fixture.componentRef.setInput('listingId', 12);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const description = root.querySelector('textarea')!;
    description.value = 'This needs investigation.';
    description.dispatchEvent(new Event('input'));
    root.querySelector('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    const http = TestBed.inject(HttpTestingController);
    const request = http.expectOne('/api/v1/me/reports/');
    expect(request.request.body.listing).toBe(12);
    request.flush({}, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(description.value).toBe('This needs investigation.');
    expect(root.textContent).toContain('try again');
    root.querySelector('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    http.expectOne('/api/v1/me/reports/').flush({ id: 'receipt-123' });
    fixture.detectChanges();
    expect(root.textContent).toContain('receipt-123');
    expect(root.querySelector('form')).toBeNull();
    http.verify();
  });
});
