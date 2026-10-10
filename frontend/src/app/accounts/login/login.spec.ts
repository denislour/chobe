import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Login } from './login';

describe('Login', () => {
  let fixture: ComponentFixture<Login>;
  let http: HttpTestingController;
  let element: HTMLElement;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [Login],
      providers: [provideHttpClient(), provideHttpClientTesting()],
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
    http.expectOne('/api/v1/auth/csrf/').flush(null, { status: 204, statusText: 'No Content' });
    return http.expectOne('/api/v1/auth/login/');
  }

  it('validates missing fields without sending a request', () => {
    element.querySelector('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    fixture.detectChanges();
    expect(element.textContent).toContain('Enter your username or email.');
    expect(element.textContent).toContain('Enter your password.');
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
    fixture.componentInstance.submit();
    loginRequest().flush({ id: 1, username: 'admin' });
    fixture.detectChanges();
    expect(element.querySelector('[role=status]')!.textContent).toContain('logged in as admin');
    expect(fixture.componentInstance.form.controls.password.value).toBe('');
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

  it('gets a new CSRF cookie when retrying a failed login', () => {
    submit();
    loginRequest().flush({}, { status: 403, statusText: 'Forbidden' });
    submit();
    loginRequest().flush({ id: 1, username: 'admin' });
    fixture.detectChanges();
    expect(element.querySelector('[role=alert]')).toBeNull();
    expect(element.querySelector('[role=status]')).not.toBeNull();
  });
});
