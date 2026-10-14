import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { ResetPassword } from './reset-password';

describe('ResetPassword', () => {
  let fixture: ComponentFixture<ResetPassword>;
  let http: HttpTestingController;
  let element: HTMLElement;
  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [ResetPassword],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ uid: 'MQ', token: 'token' }) } },
        },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ResetPassword);
    await fixture.whenStable();
    element = fixture.nativeElement;
  });
  afterEach(() => http.verify());

  function submit(password = 'new-safe-password', confirmation = password): void {
    for (const [id, value] of [
      ['reset-password', password],
      ['reset-confirm', confirmation],
    ]) {
      const input = element.querySelector<HTMLInputElement>(`#${id}`)!;
      input.value = value;
      input.dispatchEvent(new Event('input'));
    }
    element
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
  }

  it('requires matching passwords before making a request', () => {
    submit('new-safe-password', 'different-password');
    http.expectNone('/api/v1/auth/reset-password/');
    expect(element.textContent).toContain('same password');
  });

  it('accepts matching passwords after correcting only the first field', () => {
    submit('first-password', 'corrected-password');
    const input = element.querySelector<HTMLInputElement>('#reset-password')!;
    input.value = 'corrected-password';
    input.dispatchEvent(new Event('input'));
    element
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    http
      .expectOne('/api/v1/auth/reset-password/')
      .flush(null, { status: 204, statusText: 'No Content' });
  });

  it('uses the link token, blocks duplicate submits and clears password on success', async () => {
    submit();
    const request = http.expectOne('/api/v1/auth/reset-password/');
    expect(request.request.body).toEqual({
      uid: 'MQ',
      token: 'token',
      password: 'new-safe-password',
      password_confirm: 'new-safe-password',
    });
    submit();
    http.expectNone('/api/v1/auth/reset-password/');
    request.flush(null, { status: 204, statusText: 'No Content' });
    fixture.detectChanges();
    await fixture.whenStable();
    expect(element.querySelector('[role=status]')!.textContent).toContain(
      'password has been reset',
    );
    expect(element.querySelector('form')).toBeNull();
  });

  it('shows an expired link error and a link to request a new one', () => {
    submit();
    http
      .expectOne('/api/v1/auth/reset-password/')
      .flush(
        { non_field_errors: ['This reset link has expired.'] },
        { status: 400, statusText: 'Invalid' },
      );
    fixture.detectChanges();
    expect(element.querySelector('[role=alert]')!.textContent).toContain('expired');
    expect(element.querySelector('a[href="/forgot-password"]')).not.toBeNull();
  });

  it('shows backend password validation next to the confirmation field', () => {
    submit();
    http
      .expectOne('/api/v1/auth/reset-password/')
      .flush(
        { password_confirm: ['This password is too common.'] },
        { status: 400, statusText: 'Invalid' },
      );
    fixture.detectChanges();
    expect(element.querySelector('#reset-confirm-error')!.textContent).toContain('too common');
    expect(element.querySelector('#reset-confirm')!.getAttribute('aria-invalid')).toBe('true');
  });

  it('can show or hide both password inputs', () => {
    element.querySelector<HTMLButtonElement>('.password-toggle')!.click();
    fixture.detectChanges();
    expect(
      [...element.querySelectorAll<HTMLInputElement>('input')].every(
        (input) => input.type === 'text',
      ),
    ).toBe(true);
  });
});
