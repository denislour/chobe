import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { AuthStore } from '../auth.store';
import { Register } from './register';

describe('Register', () => {
  let fixture: ComponentFixture<Register>;
  let http: HttpTestingController;
  let element: HTMLElement;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [Register],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
          { path: 'login', loadComponent: () => import('../login/login').then((m) => m.Login) },
        ]),
      ],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Register);
    await fixture.whenStable();
    element = fixture.nativeElement;
  });
  afterEach(() => http.verify());

  function fillForm(
    username = 'new_member',
    email = 'member@example.com',
    password = 'demo-password',
  ): void {
    for (const [id, value] of [
      ['username', username],
      ['email', email],
      ['password', password],
    ]) {
      const input = element.querySelector<HTMLInputElement>(`#register-${id}`)!;
      input.value = value;
      input.dispatchEvent(new Event('input'));
    }
    const terms = element.querySelector<HTMLInputElement>('#register-terms')!;
    terms.checked = true;
    terms.dispatchEvent(new Event('change'));
  }

  function submit(): void {
    element
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
  }

  it('validates required fields without sending an API request', () => {
    submit();
    expect(element.textContent).toContain('Enter a valid username');
    expect(element.textContent).toContain('Enter a valid email');
    expect(element.textContent).toContain('Use a password with 8 to 128 characters');
    expect(element.textContent).toContain('Accept the terms');
    http.expectNone('/api/v1/auth/register/');
  });

  for (const [username, email, password] of [
    ['n@m', 'member@example.com', 'demo-password'],
    ['valid_name', 'invalid', 'demo-password'],
    ['valid_name', 'member@example.com', 'short'],
  ]) {
    it(`rejects invalid input ${username}/${email}/${password}`, () => {
      fillForm(username, email, password);
      submit();
      http.expectNone('/api/v1/auth/register/');
    });
  }

  it('requires acceptance of the terms', () => {
    fillForm();
    element.querySelector<HTMLInputElement>('#register-terms')!.click();
    submit();
    http.expectNone('/api/v1/auth/register/');
    expect(element.textContent).toContain('Accept the terms');
  });

  it('toggles password visibility without submitting', () => {
    const toggle = element.querySelector<HTMLButtonElement>('.password-toggle')!;
    toggle.click();
    fixture.detectChanges();
    expect(element.querySelector<HTMLInputElement>('#register-password')!.type).toBe('text');
    expect(toggle.getAttribute('aria-pressed')).toBe('true');
    toggle.click();
    fixture.detectChanges();
    expect(element.querySelector<HTMLInputElement>('#register-password')!.type).toBe('password');
    http.expectNone('/api/v1/auth/register/');
  });

  it('creates a shared session, prevents duplicate submit and opens the signed-in screen', async () => {
    fillForm();
    submit();
    expect(element.querySelector<HTMLButtonElement>('button[type=submit]')!.disabled).toBe(true);
    submit();
    const request = http.expectOne('/api/v1/auth/register/');
    expect(request.request.body).toEqual({
      username: 'new_member',
      email: 'member@example.com',
      password: 'demo-password',
      accept_terms: true,
    });
    request.flush({ id: 2, username: 'new_member' }, { status: 201, statusText: 'Created' });
    await fixture.whenStable();
    expect(TestBed.inject(AuthStore).user()?.username).toBe('new_member');
    expect(TestBed.inject(Router).url).toBe('/login');
    expect(element.querySelector<HTMLInputElement>('#register-password')!.value).toBe('');
  });

  it('shows field errors and preserves input for retry', () => {
    fillForm();
    submit();
    http
      .expectOne('/api/v1/auth/register/')
      .flush(
        { email: ['This email is already in use.'], password: ['This password is too common.'] },
        { status: 400, statusText: 'Bad Request' },
      );
    fixture.detectChanges();
    expect(element.querySelector('#register-email-error')!.textContent).toContain('already in use');
    expect(element.querySelector('#register-password-error')!.textContent).toContain('too common');
    expect(element.querySelector<HTMLInputElement>('#register-email')!.value).toBe(
      'member@example.com',
    );
    expect(
      element.querySelector<HTMLInputElement>('#register-email')!.getAttribute('aria-invalid'),
    ).toBe('true');
    submit();
    expect(element.querySelector('#register-email-error')!.textContent?.trim()).toBe('');
    http
      .expectOne('/api/v1/auth/register/')
      .flush(null, { status: 503, statusText: 'Unavailable' });
  });

  for (const [status, message] of [
    [403, 'Reload this page'],
    [429, 'Too many sign-up attempts'],
    [503, 'Unable to create your account'],
  ] as const) {
    it(`handles HTTP ${status} without retrying automatically`, () => {
      fillForm();
      submit();
      http.expectOne('/api/v1/auth/register/').flush(null, { status, statusText: 'Error' });
      fixture.detectChanges();
      expect(element.querySelector('[role=alert]')!.textContent).toContain(message);
      expect(element.querySelector<HTMLButtonElement>('button[type=submit]')!.disabled).toBe(false);
      http.expectNone('/api/v1/auth/register/');
      http.expectNone('/api/v1/auth/csrf/');
    });
  }

  it('retries the session check when startup failed', () => {
    void TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush(null, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    element.querySelector<HTMLButtonElement>('.btn')!.click();
    http.expectOne('/api/v1/auth/session/').flush({ user: null });
    fixture.detectChanges();
    expect(element.querySelector('[role=alert]')).toBeNull();
  });

  it('keeps registration running in the root store after leaving the component', () => {
    fillForm();
    submit();
    const request = http.expectOne('/api/v1/auth/register/');
    fixture.destroy();
    expect(request.cancelled).toBe(false);
    request.flush({ id: 2, username: 'new_member' }, { status: 201, statusText: 'Created' });
    expect(TestBed.inject(AuthStore).user()?.username).toBe('new_member');
    expect(TestBed.inject(AuthStore).pending()).toBe(false);
  });
});
