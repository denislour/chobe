import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { listingFixture } from '@app/domain/listing/listing-fixtures';
import { HomeStore } from './home.store';
describe('HomeStore', () => {
  it('keeps listings visible when the category section fails', () => {
    TestBed.configureTestingModule({
      providers: [HomeStore, provideHttpClient(), provideHttpClientTesting()],
    });
    const store = TestBed.inject(HomeStore);
    const http = TestBed.inject(HttpTestingController);
    store.loadCategories();
    store.loadListings();
    http.expectOne('/api/v1/categories/').flush({}, { status: 503, statusText: 'Unavailable' });
    http.expectOne('/api/v1/listings/').flush({ results: [listingFixture], count: 1 });
    expect(store.categoriesError()).toContain('try again');
    expect(store.listings()[0].id).toBe(12);
    store.loadCategories();
    http.expectOne('/api/v1/categories/').flush([]);
    expect(store.categoriesError()).toBe('');
    http.verify();
  });
});
