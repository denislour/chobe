import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { privacyFixture } from '@app/accounts/account-fixtures';
import { AuthStore } from '@app/auth/auth.store';
import { Privacy } from './privacy';

describe('Privacy', () => {
  let fixture: ComponentFixture<Privacy>;
  let http: HttpTestingController;
  let element: HTMLElement;
  beforeEach(async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    TestBed.configureTestingModule({
      imports: [Privacy],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
    fixture = TestBed.createComponent(Privacy);
    fixture.detectChanges();
    http.expectOne('/api/v1/me/privacy-settings/').flush(privacyFixture);
    http.expectOne('/api/v1/me/viewing-history/').flush([]);
    await fixture.whenStable();
    element = fixture.nativeElement;
  });
  afterEach(() => {
    TestBed.resetTestingModule();
    http.verify();
    vi.useRealTimers();
  });

  it('saves explicit phone consent and the loaded version', async () => {
    const checkbox = element.querySelector<HTMLInputElement>('#share-phone')!;
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event('change'));
    element
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    const request = http.expectOne('/api/v1/me/privacy-settings/');
    expect(request.request.body).toEqual({ share_phone: true, record_history: true, version: 1 });
    request.flush({ ...privacyFixture, share_phone: true, version: 2 });
    await fixture.whenStable();
    expect(element.textContent).toContain('Privacy settings saved.');
  });

  it('shows the missing phone message in a dismissible notification without reload', async () => {
    const checkbox = element.querySelector<HTMLInputElement>('#share-phone')!;
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event('change'));
    const historyCheckbox = element.querySelector<HTMLInputElement>('#record-history')!;
    historyCheckbox.checked = false;
    historyCheckbox.dispatchEvent(new Event('change'));
    element
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    http
      .expectOne('/api/v1/me/privacy-settings/')
      .flush(
        { share_phone: ['Add a phone number first.'] },
        { status: 400, statusText: 'Bad Request' },
      );
    await fixture.whenStable();
    expect(checkbox.checked).toBe(false);
    expect(historyCheckbox.checked).toBe(true);
    expect(element.querySelector('.notification [role="alert"]')?.textContent).toContain(
      'Add a phone number first.',
    );
    expect(element.textContent).not.toContain('Check the highlighted fields.');
    expect(element.textContent).not.toContain('Reload latest values');
    element
      .querySelector<HTMLButtonElement>('[aria-label="Dismiss privacy notification"]')!
      .click();
    await fixture.whenStable();
    expect(element.querySelector('.notification')).toBeNull();
    expect(checkbox.checked).toBe(false);
    expect(element.querySelector('#consent-error')?.textContent).toContain(
      'Add a phone number first.',
    );
  });

});
