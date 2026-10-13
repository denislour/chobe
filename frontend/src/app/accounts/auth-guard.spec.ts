import { Component } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { authGuard } from './auth-guard';
import { AuthStore } from '@app/accounts/store/auth.store';
import { Login } from '@app/accounts/login/login';
import { Register } from '@app/accounts/register/register';

@Component({ selector: 'app-test-destination', template: 'Protected action' })
class TestDestination {}

describe('authGuard and login return URL', () => {
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
          { path: 'login', component: Login },
          { path: 'register', component: Register },
          { path: 'saved', component: TestDestination, canActivate: [authGuard] },
        ]),
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('takes a guest through login and back to the intended action', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/saved?sort=new#item', Login);
    expect(TestBed.inject(Router).url).toContain('/login?returnUrl=');
    const element = harness.routeNativeElement!;
    for (const [id, value] of [
      ['login-username', 'member'],
      ['login-password', 'safe-password'],
    ]) {
      const input = element.querySelector<HTMLInputElement>(`#${id}`)!;
      input.value = value;
      input.dispatchEvent(new Event('input'));
    }
    element
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    http.expectOne('/api/v1/auth/login/').flush({ id: 1, username: 'member' });
    harness.detectChanges();
    await harness.fixture.whenStable();
    expect(TestBed.inject(Router).url).toBe('/saved?sort=new#item');
    expect(harness.routeNativeElement!.textContent).toContain('Protected action');
  });

  it('allows an already restored session to access the action', async () => {
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/saved', TestDestination);
    expect(TestBed.inject(Router).url).toBe('/saved');
  });

  it('takes registration back to the same intended action', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/register?returnUrl=%2Fsaved%3Fsort%3Dnew', Register);
    const element = harness.routeNativeElement!;
    for (const [id, value] of [
      ['register-username', 'member'],
      ['register-email', 'member@example.com'],
      ['register-password', 'safe-password'],
    ]) {
      const input = element.querySelector<HTMLInputElement>(`#${id}`)!;
      input.value = value;
      input.dispatchEvent(new Event('input'));
    }
    const terms = element.querySelector<HTMLInputElement>('#register-terms')!;
    terms.checked = true;
    terms.dispatchEvent(new Event('change'));
    element
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    http
      .expectOne('/api/v1/auth/register/')
      .flush({ id: 1, username: 'member' }, { status: 201, statusText: 'Created' });
    harness.detectChanges();
    await harness.fixture.whenStable();
    expect(TestBed.inject(Router).url).toBe('/saved?sort=new');
  });

  it('keeps the intended action when session checking fails and resumes after retry', async () => {
    const auth = TestBed.inject(AuthStore);
    const restoration = auth.restoreSession();
    http.expectOne('/api/v1/auth/session/').flush(null, { status: 503, statusText: 'Unavailable' });
    await restoration;
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/saved', Login);
    expect(TestBed.inject(Router).url).toContain('returnUrl=');
    const retry = auth.restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await retry;
    harness.detectChanges();
    await harness.fixture.whenStable();
    expect(TestBed.inject(Router).url).toBe('/saved');
  });

  it('keeps the login page when the return URL points outside the app', async () => {
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/login?returnUrl=https%3A%2F%2Fattacker.example', Login);
    expect(TestBed.inject(Router).url).toContain('/login');
  });
});
