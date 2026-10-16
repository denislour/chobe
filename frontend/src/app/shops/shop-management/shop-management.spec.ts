import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { AuthStore } from '@app/auth/auth.store';
import { shopFixture } from '@app/shops/shop-fixtures';
import { ShopStore } from '@app/shops/shop.store';
import { ShopManagement } from './shop-management';

describe('ShopManagement', () => {
  let fixture: ComponentFixture<ShopManagement>;
  let http: HttpTestingController;
  let element: HTMLElement;
  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [ShopManagement],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
    fixture = TestBed.createComponent(ShopManagement);
    fixture.detectChanges();
    http.expectOne('/api/v1/me/shop/').flush(shopFixture);
    await fixture.whenStable();
    element = fixture.nativeElement;
  });
  afterEach(() => { http.verify(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

  function click(text: string): void {
    [...element.querySelectorAll<HTMLButtonElement>('button')].find((button) => button.textContent?.includes(text))!.click();
  }

  function enter(id: string, value: string): void {
    const input = element.querySelector<HTMLInputElement>(`#${id}`)!;
    input.value = value;
    input.dispatchEvent(new Event('input'));
  }

  function submit(): void {
    element.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  }

  it('creates a first shop after the owner endpoint reports no shop', async () => {
    fixture.debugElement.injector.get(ShopStore).load();
    http.expectOne('/api/v1/me/shop/').flush({}, { status: 404, statusText: 'Not Found' });
    await fixture.whenStable();
    expect(element.textContent).toContain('Create your shop');
    enter('shop-name', shopFixture.name);
    enter('shop-slug', shopFixture.slug);
    enter('shop-area', shopFixture.area);
    enter('shop-description', shopFixture.description);
    submit();
    const request = http.expectOne('/api/v1/shops/');
    expect((request.request.body as FormData).has('version')).toBe(false);
    request.flush(shopFixture);
    await fixture.whenStable();
    expect(element.textContent).toContain('Shop saved.');
  });

  it('submits the current version and keeps edits after a conflict', async () => {
    enter('shop-name', 'Moc Living');
    submit();
    const request = http.expectOne(`/api/v1/shops/${shopFixture.id}/`);
    expect((request.request.body as FormData).get('version')).toBe('1');
    expect((request.request.body as FormData).get('name')).toBe('Moc Living');
    request.flush({}, { status: 409, statusText: 'Conflict' });
    await fixture.whenStable();
    expect(element.querySelector<HTMLInputElement>('#shop-name')!.value).toBe('Moc Living');
    expect(element.textContent).toContain('changed');
  });

  it('shows an unsaved preview without a mutation request', async () => {
    enter('shop-name', 'Moc Living');
    click('Preview changes');
    await fixture.whenStable();
    expect(element.querySelector('app-shop-card')?.textContent).toContain('Moc Living');
    http.expectNone(`/api/v1/shops/${shopFixture.id}/`);
  });

  it('blocks invalid shop addresses before submitting', async () => {
    enter('shop-slug', 'Invalid Address');
    submit();
    await fixture.whenStable();
    expect(element.textContent).toContain('Use an address');
    http.expectNone(`/api/v1/shops/${shopFixture.id}/`);
  });

  it('requires an explicit confirmation before pausing', async () => {
    click('Pause shop');
    await fixture.whenStable();
    http.expectNone(`/api/v1/shops/${shopFixture.id}/status/`);
    click('Confirm pause');
    const request = http.expectOne(`/api/v1/shops/${shopFixture.id}/status/`);
    expect(request.request.body).toEqual({ status: 'paused', version: 1 });
    request.flush({ ...shopFixture, status: 'paused', version: 2 });
    await fixture.whenStable();
    expect(element.textContent).toContain('Reopen shop');
  });

  it('requires the shop name before confirming permanent closure', async () => {
    click('Close shop');
    await fixture.whenStable();
    const confirm = [...element.querySelectorAll<HTMLButtonElement>('button')].find((button) => button.textContent?.includes('Confirm closure'))!;
    expect(confirm.disabled).toBe(true);
    enter('close-confirmation', shopFixture.name);
    await fixture.whenStable();
    confirm.click();
    http.expectOne(`/api/v1/shops/${shopFixture.id}/status/`).flush({ ...shopFixture, status: 'closed', version: 2 });
    await fixture.whenStable();
    expect(element.querySelector<HTMLFieldSetElement>('fieldset')!.disabled).toBe(true);
    expect(element.textContent).toContain('permanently closed');
  });

  it('keeps a selected image until save completes and releases its preview', async () => {
    vi.stubGlobal('URL', class extends URL {
      static override createObjectURL = vi.fn(() => 'blob:shop-logo');
      static override revokeObjectURL = vi.fn();
    });
    const input = element.querySelector<HTMLInputElement>('#shop-logo')!;
    const file = new File(['image'], 'logo.png', { type: 'image/png' });
    Object.defineProperty(input, 'files', { configurable: true, value: [file] });
    input.dispatchEvent(new Event('change'));
    await fixture.whenStable();
    submit();
    const request = http.expectOne(`/api/v1/shops/${shopFixture.id}/`);
    expect((request.request.body as FormData).get('logo')).toBe(file);
    request.flush({ ...shopFixture, logo_url: '/api/v1/shops/logo/', version: 2 });
    await fixture.whenStable();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:shop-logo');
    expect(input.value).toBe('');
  });
});
