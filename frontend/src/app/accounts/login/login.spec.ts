import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthStore } from '../store/auth.store';
import { Login } from './login';

describe('Login', () => {
  let fixture: ComponentFixture<Login>;
  let http: HttpTestingController;
  let element: HTMLElement;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [Login],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Login);
    await fixture.whenStable();
    element = fixture.nativeElement;
  });
  afterEach(() => http.verify());

  function submit() {
    for (const [id, value] of [
      ['login-username', 'admin'],
      ['login-password', 'demo-password'],
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

  function loginRequest() {
    return http.expectOne('/api/v1/auth/login/');
  }

  it('validates missing fields without sending a request', () => {
    element.querySelector('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    fixture.detectChanges();
    expect(element.textContent).toContain('Enter your username or email.');
    expect(element.textContent).toContain('Enter your password.');
    http.expectNone('/api/v1/auth/login/');
    http.expectNone('/api/v1/auth/csrf/');
  });

  it('shows and hides the password', () => {
    const button = element.querySelector<HTMLButtonElement>('.password-toggle')!;
    button.click();
    fixture.detectChanges();
    expect(element.querySelector<HTMLInputElement>('#login-password')!.type).toBe('text');
    button.click();
    fixture.detectChanges();
    expect(element.querySelector<HTMLInputElement>('#login-password')!.type).toBe('password');
  });

  it('prevents repeated submits while logging in and clears the password on success', () => {
    submit();
    expect(element.querySelector<HTMLButtonElement>('button[type=submit]')!.disabled).toBe(true);
    element.querySelector('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    loginRequest().flush({ id: 1, username: 'admin' });
    fixture.detectChanges();
    expect(element.querySelector('[role=status]')!.textContent).toContain('logged in as admin');
    expect(element.querySelector('form')).toBeNull();
  });

  for (const [status, text] of [
    [400, 'Invalid username or password.'],
    [403, 'Your security check expired.'],
    [429, 'Too many login attempts.'],
    [500, 'Unable to connect.'],
  ] as const) {
    it(`shows a recoverable error for status ${status}`, () => {
      submit();
      loginRequest().flush({}, { status, statusText: 'Error' });
      fixture.detectChanges();
      expect(element.querySelector('[role=alert]')!.textContent).toContain(text);
      expect(element.querySelector<HTMLInputElement>('#login-username')!.value).toBe('admin');
      expect(element.querySelector<HTMLButtonElement>('button[type=submit]')!.disabled).toBe(false);
    });
  }

  it('asks for reload on CSRF failure without fetching or retrying automatically', () => {
    submit();
    loginRequest().flush({}, { status: 403, statusText: 'Forbidden' });
    fixture.detectChanges();
    expect(element.querySelector('[role=alert]')!.textContent).toContain('Reload this page');
    http.expectNone('/api/v1/auth/csrf/');
    http.expectNone('/api/v1/auth/login/');
  });

  it('logs out and returns to the empty login form', () => {
    submit();
    loginRequest().flush({ id: 1, username: 'admin' });
    fixture.detectChanges();
    element.querySelector<HTMLButtonElement>('.btn')!.click();
    fixture.detectChanges();
    expect(element.textContent).toContain('Logging out…');
    http.expectOne('/api/v1/auth/logout/').flush(null, { status: 204, statusText: 'No Content' });
    fixture.detectChanges();
    expect(element.querySelector('form')).not.toBeNull();
    expect(TestBed.inject(AuthStore).user()).toBeNull();
    for (const id of ['login-username', 'login-password']) {
      expect(element.querySelector<HTMLInputElement>(`#${id}`)!.value).toBe('');
    }
    expect(element.querySelector<HTMLInputElement>('#login-password')!.type).toBe('password');
  });

  it('shows a restored session and retries a failed session check', () => {
    void TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush(null, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(element.textContent).toContain('Unable to check your session');
    submit();
    loginRequest().flush(null, { status: 400, statusText: 'Bad Request' });
    fixture.detectChanges();
    expect(element.querySelector('[role=alert]')!.textContent).toContain(
      'Invalid username or password',
    );
    element.querySelector<HTMLButtonElement>('.btn')!.click();
    fixture.detectChanges();
    expect(element.textContent).toContain('Checking session…');
    expect(element.querySelector('[role=alert]')!.textContent).not.toContain(
      'Invalid username or password',
    );
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'admin' } });
    fixture.detectChanges();
    expect(element.querySelector('form')).toBeNull();
    expect(element.querySelector('[role=status]')!.textContent).toContain('logged in as admin');
    expect(element.querySelector('[role=alert]')).toBeNull();
  });

  it('keeps the user and enables retry when logout fails', () => {
    submit();
    loginRequest().flush({ id: 1, username: 'admin' });
    fixture.detectChanges();
    element.querySelector<HTMLButtonElement>('.btn')!.click();
    http.expectOne('/api/v1/auth/logout/').flush(null, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(element.querySelector('[role=alert]')!.textContent).toContain('Unable to log out');
    expect(TestBed.inject(AuthStore).user()?.username).toBe('admin');
    expect(element.querySelector<HTMLButtonElement>('.btn')!.disabled).toBe(false);
  });

  it('keeps the shared login request alive when the component is destroyed', () => {
    submit();
    const request = loginRequest();
    fixture.destroy();
    expect(request.cancelled).toBe(false);
    request.flush({ id: 1, username: 'admin' });
    expect(TestBed.inject(AuthStore).user()?.username).toBe('admin');
    expect(TestBed.inject(AuthStore).pending()).toBe(false);
  });
});
