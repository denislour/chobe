import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from '@app/app.routes';
import { AuthStore } from '@app/auth/auth.store';
import { categoryFixture } from '@app/domain/category/category-fixtures';
import { draftFixture } from '@app/domain/listing/listing-fixtures';

describe('Listing editor', () => {
  it('loads typed attributes, preserves unsaved text on conflict and does not submit automatically', async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)],
    });
    const http = TestBed.inject(HttpTestingController);
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
    const harness = await RouterTestingHarness.create('/seller/listings/12/edit');
    http.expectOne('/api/v1/categories/').flush([categoryFixture]);
    http.expectOne('/api/v1/me/listings/12/').flush(draftFixture);
    http.expectOne('/api/v1/me/listings/12/moderation/').flush([]);
    http.expectOne('/api/v1/me/listings/12/history/').flush([]);
    harness.detectChanges();
    const root = harness.routeNativeElement!;
    const title = root.querySelector<HTMLInputElement>('#listing-title')!;
    title.value = 'Unsaved new title';
    title.dispatchEvent(new Event('input'));
    harness.detectChanges();
    title.closest('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    const request = http.expectOne('/api/v1/me/listings/12/');
    expect(request.request.body.attributes).toEqual({ storage_gb: 128, tested: false });
    expect(request.request.body.version).toBe(4);
    request.flush({}, { status: 409, statusText: 'Conflict' });
    harness.detectChanges();
    expect(title.value).toBe('Unsaved new title');
    expect(root.textContent).toContain('Reload the latest');
    http.expectNone('/api/v1/me/listings/12/submit/');
    http.verify();
  });
  it('opens the saved draft after first save without asking to discard saved attributes', async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)],
    });
    const http = TestBed.inject(HttpTestingController);
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'member' } });
    await restoration;
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const harness = await RouterTestingHarness.create('/seller/listings/new');
    http.expectOne('/api/v1/categories/').flush([categoryFixture]);
    harness.detectChanges();
    const root = harness.routeNativeElement!;
    const category = root.querySelector<HTMLSelectElement>('#listing-category')!;
    category.value = categoryFixture.id;
    category.dispatchEvent(new Event('change'));
    harness.detectChanges();
    const storage = root.querySelector<HTMLInputElement>('#listing-storage_gb')!;
    storage.value = '128';
    storage.dispatchEvent(new Event('input'));
    const title = root.querySelector<HTMLInputElement>('#listing-title')!;
    title.value = 'New draft';
    title.dispatchEvent(new Event('input'));
    title.closest('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    http
      .expectOne('/api/v1/me/listings/')
      .flush({ ...draftFixture, title: 'New draft', status: 'draft', version: 1 });
    http.expectOne('/api/v1/me/listings/12/moderation/').flush([]);
    http.expectOne('/api/v1/me/listings/12/history/').flush([]);
    harness.detectChanges();
    await harness.fixture.whenStable();
    expect(confirm).not.toHaveBeenCalled();
    http.expectOne('/api/v1/categories/').flush([categoryFixture]);
    http
      .expectOne('/api/v1/me/listings/12/')
      .flush({ ...draftFixture, title: 'New draft', status: 'draft', version: 1 });
    http.expectOne('/api/v1/me/listings/12/moderation/').flush([]);
    http.expectOne('/api/v1/me/listings/12/history/').flush([]);
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('Version 1');
    confirm.mockRestore();
    http.verify();
  });
});
