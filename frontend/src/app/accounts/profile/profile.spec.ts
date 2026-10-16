import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { profileFixture } from '@app/accounts/account-fixtures';
import { AuthStore } from '@app/auth/auth.store';
import { Profile } from './profile';

describe('Profile', () => {
  let fixture: ComponentFixture<Profile>;
  let http: HttpTestingController;
  let element: HTMLElement;
  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [Profile],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
    fixture = TestBed.createComponent(Profile);
    fixture.detectChanges();
    http.expectOne('/api/v1/profiles/me/').flush(profileFixture);
    await fixture.whenStable();
    element = fixture.nativeElement;
  });
  afterEach(() => http.verify());

  function submit(): void {
    element
      .querySelector('form')!
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
  }

  it('renders read-only email and saves the current version', async () => {
    const input = element.querySelector<HTMLInputElement>('#profile-name')!;
    input.value = 'Updated member';
    input.dispatchEvent(new Event('input'));
    expect(element.querySelector<HTMLInputElement>('#profile-email')!.readOnly).toBe(true);
    submit();
    const request = http.expectOne('/api/v1/profiles/me/');
    const body = request.request.body as FormData;
    expect(body.get('display_name')).toBe('Updated member');
    expect(body.get('version')).toBe('1');
    request.flush({ ...profileFixture, display_name: 'Updated member', version: 2 });
    await fixture.whenStable();
    expect(element.textContent).toContain('Profile saved.');
  });

  it('keeps unsaved fields on conflict and reloads only after an explicit request', async () => {
    const input = element.querySelector<HTMLInputElement>('#profile-name')!;
    input.value = 'Unsaved name';
    input.dispatchEvent(new Event('input'));
    submit();
    http.expectOne('/api/v1/profiles/me/').flush({}, { status: 409, statusText: 'Conflict' });
    await fixture.whenStable();
    expect(input.value).toBe('Unsaved name');
    expect(element.textContent).toContain('changed');
    const reload = [...element.querySelectorAll<HTMLButtonElement>('button')].find((button) =>
      button.textContent?.includes('Reload latest'),
    )!;
    reload.click();
    http.expectOne('/api/v1/profiles/me/').flush({ ...profileFixture, version: 3 });
    await fixture.whenStable();
    expect(input.value).toBe('Member');
  });

  it('blocks an invalid phone before making a request', async () => {
    const input = element.querySelector<HTMLInputElement>('#profile-phone')!;
    input.value = '0912345678';
    input.dispatchEvent(new Event('input'));
    submit();
    http.expectNone('/api/v1/profiles/me/');
    await fixture.whenStable();
    expect(element.textContent).toContain('8 to 15 digits');
  });

  it('uploads a selected file as multipart and clears the file after success', async () => {
    const input = element.querySelector<HTMLInputElement>('#profile-avatar')!;
    const file = new File(['image'], 'avatar.png', { type: 'image/png' });
    Object.defineProperty(input, 'files', { configurable: true, value: [file] });
    input.dispatchEvent(new Event('change'));
    submit();
    const request = http.expectOne('/api/v1/profiles/me/');
    expect((request.request.body as FormData).get('avatar')).toBe(file);
    request.flush({
      ...profileFixture,
      version: 2,
      avatar_url: '/api/v1/profiles/me/avatar/?version=2',
    });
    await fixture.whenStable();
    expect(element.querySelector('img')?.getAttribute('src')).toContain('version=2');
    expect(input.value).toBe('');
  });
});
