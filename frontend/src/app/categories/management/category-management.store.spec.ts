import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import {
  categoryDraftFixture,
  taxonomyCapabilitiesFixture,
} from '@app/domain/category/category-fixtures';
import { CategoryManagementStore } from './category-management.store';

describe('CategoryManagementStore', () => {
  let http: HttpTestingController;
  let store: CategoryManagementStore;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CategoryManagementStore, provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    store = TestBed.inject(CategoryManagementStore);
  });
  afterEach(() => http.verify());

  it('keeps the existing draft and permits retry after a version conflict', () => {
    const base = `/api/v1/admin/categories/${categoryDraftFixture.id}/`;
    store.select(categoryDraftFixture.id);
    http.expectOne(base).flush(categoryDraftFixture);
    http.expectOne(`${base}revisions/`).flush([]);
    http.expectOne(`${base}history/`).flush([]);
    const change = { id: categoryDraftFixture.id, version: 2, action: 'publish' as const };
    store.transition(change);
    store.transition(change);
    http.expectOne(`${base}publish/`).flush({}, { status: 409, statusText: 'Conflict' });
    expect(store.pending()).toBe(false);
    expect(store.draft()).toEqual(categoryDraftFixture);
    expect(store.error()).toContain('another session');
    store.transition(change);
    http.expectOne(`${base}publish/`).flush({ ...categoryDraftFixture, version: 3 });
    http.expectOne(base).flush({ ...categoryDraftFixture, version: 3 });
    http.expectOne(`${base}revisions/`).flush([]);
    http.expectOne(`${base}history/`).flush([]);
    expect(store.draft()?.version).toBe(3);
    expect(store.notice()).toContain('published');
  });

  it('loads capabilities from the server and can recover after access is denied', () => {
    store.load();
    http.expectOne('/api/v1/admin/categories/').flush([], { status: 403, statusText: 'Forbidden' });
    http.expectOne('/api/v1/admin/categories/capabilities/');
    expect(store.capabilities()).toBeNull();
    expect(store.loading()).toBe(false);
    store.load();
    http.expectOne('/api/v1/admin/categories/').flush([]);
    http.expectOne('/api/v1/admin/categories/capabilities/').flush(taxonomyCapabilitiesFixture);
    expect(store.capabilities()?.publish).toBe(true);
    expect(store.error()).toBe('');
  });
});
