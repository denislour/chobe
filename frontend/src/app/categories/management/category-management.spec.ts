import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from '@app/app.routes';
import { AuthStore } from '@app/auth/auth.store';
import {
  categoryDraftFixture,
  taxonomyCapabilitiesFixture,
} from '@app/categories/category-fixtures';

describe('CategoryManagement', () => {
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)],
    });
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  async function restoreSession(): Promise<void> {
    const restoration = TestBed.inject(AuthStore).restoreSession();
    http.expectOne('/api/v1/auth/session/').flush({ user: { id: 1, username: 'admin' } });
    await restoration;
  }

  it('redirects guests without making management requests', async () => {
    await RouterTestingHarness.create('/admin/categories');
    expect(TestBed.inject(Router).url).toContain('/login?');
    http.expectNone('/api/v1/admin/categories/');
  });

  it('shows denied access from the server without exposing an editor', async () => {
    await restoreSession();
    const harness = await RouterTestingHarness.create('/admin/categories');
    const list = http.expectOne('/api/v1/admin/categories/');
    const permissions = http.expectOne('/api/v1/admin/categories/capabilities/');
    list.flush({}, { status: 403, statusText: 'Forbidden' });
    expect(permissions.cancelled).toBe(true);
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('Taxonomy access required');
    expect(harness.routeNativeElement?.querySelector('form')).toBeNull();
  });

  it('requires confirmation before publishing and shows the resulting version', async () => {
    await restoreSession();
    const harness = await RouterTestingHarness.create('/admin/categories');
    http.expectOne('/api/v1/admin/categories/').flush([categoryDraftFixture]);
    http.expectOne('/api/v1/admin/categories/capabilities/').flush(taxonomyCapabilitiesFixture);
    harness.detectChanges();
    harness.routeNativeElement!.querySelector<HTMLButtonElement>('.category-menu button')!.click();
    const base = `/api/v1/admin/categories/${categoryDraftFixture.id}/`;
    http.expectOne(base).flush(categoryDraftFixture);
    http.expectOne(`${base}revisions/`).flush([]);
    http.expectOne(`${base}history/`).flush([]);
    harness.detectChanges();
    const publish = [
      ...harness.routeNativeElement!.querySelectorAll<HTMLButtonElement>('button'),
    ].find((button) => button.textContent?.trim() === 'Publish saved draft')!;
    publish.click();
    harness.detectChanges();
    http.expectNone(`${base}publish/`);
    const confirm = [
      ...harness.routeNativeElement!.querySelectorAll<HTMLButtonElement>('button'),
    ].find((button) => button.textContent?.trim() === 'Confirm publish')!;
    confirm.click();
    const request = http.expectOne(`${base}publish/`);
    expect(request.request.body).toEqual({ version: 2 });
    const published = { ...categoryDraftFixture, version: 3 };
    request.flush(published);
    http.expectOne(base).flush(published);
    http.expectOne(`${base}revisions/`).flush([]);
    http.expectOne(`${base}history/`).flush([]);
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('Category version published.');
    expect(harness.routeNativeElement?.textContent).toContain('Draft v3');
  });
});
