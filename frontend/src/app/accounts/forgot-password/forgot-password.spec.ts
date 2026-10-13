import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { ForgotPassword } from './forgot-password';

describe('ForgotPassword', () => {
  let fixture: ComponentFixture<ForgotPassword>;
  let http: HttpTestingController;
  let element: HTMLElement;
  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [ForgotPassword],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ForgotPassword);
    await fixture.whenStable();
    element = fixture.nativeElement;
  });
  afterEach(() => http.verify());

  function submit(email: string): void {
    const input = element.querySelector<HTMLInputElement>('#forgot-email')!;
    input.value = email;
    input.dispatchEvent(new Event('input'));
    element
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
  }

  it('validates email locally before making a request', () => {
    submit('invalid');
    http.expectNone('/api/v1/auth/forgot-password/');
    expect(element.textContent).toContain('Enter a valid email');
    expect(element.querySelector('input')!.getAttribute('aria-invalid')).toBe('true');
  });

  it('displays a generic success message for a submitted email', () => {
    submit('unknown@example.com');
    expect(element.querySelector<HTMLButtonElement>('[type=submit]')!.disabled).toBe(true);
    http
      .expectOne('/api/v1/auth/forgot-password/')
      .flush(null, { status: 202, statusText: 'Accepted' });
    fixture.detectChanges();
    expect(element.querySelector('[role=status]')!.textContent).toContain('If an account matches');
    expect(element.querySelector('form')).toBeNull();
  });

  it('keeps email and renders errors for retry', () => {
    submit('member@example.com');
    http
      .expectOne('/api/v1/auth/forgot-password/')
      .flush(null, { status: 429, statusText: 'Limited' });
    fixture.detectChanges();
    expect(element.querySelector('[role=alert]')!.textContent).toContain('Too many attempts');
    expect(element.querySelector<HTMLInputElement>('input')!.value).toBe('member@example.com');
    expect(element.querySelector<HTMLButtonElement>('[type=submit]')!.disabled).toBe(false);
  });
});
