import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { categoryDraftFixture } from '@app/domain/category/category-fixtures';
import { CategoryManagementApi } from './category-management-api';

describe('CategoryManagementApi', () => {
  it('sends the current version for saving, publishing and retiring a category', () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const api = TestBed.inject(CategoryManagementApi);
    const http = TestBed.inject(HttpTestingController);
    const id = categoryDraftFixture.id;
    api
      .save(id, {
        name: 'Devices',
        slug: 'electronics',
        description: '',
        parent: null,
        sort_order: 0,
        restricted: false,
        attributes: [],
        version: 2,
      })
      .subscribe();
    const patch = http.expectOne(`/api/v1/admin/categories/${id}/`);
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body.version).toBe(2);
    patch.flush(categoryDraftFixture);
    for (const action of ['publish', 'retire'] as const) {
      api.transition(id, action, 2).subscribe();
      const request = http.expectOne(`/api/v1/admin/categories/${id}/${action}/`);
      expect(request.request.method).toBe('POST');
      expect(request.request.body).toEqual({ version: 2 });
      request.flush(categoryDraftFixture);
    }
    http.verify();
  });
});
