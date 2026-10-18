import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { listingFixture } from '@app/domain/listing/listing-fixtures';
import { HomeStore } from './home.store';
describe('HomeStore', () => {
  it('loads both sections from the home page API', () => {
    TestBed.configureTestingModule({
      providers: [HomeStore, provideHttpClient(), provideHttpClientTesting()],
    });
    const store = TestBed.inject(HomeStore);
    const http = TestBed.inject(HttpTestingController);
    store.load();
    expect(store.categoriesLoading()).toBe(true);
    expect(store.listingsLoading()).toBe(true);
    http.expectOne('/api/v1/home/').flush({ categories: [], latest: [listingFixture] });
    expect(store.listings()[0].id).toBe(12);
    expect(store.categoriesLoading()).toBe(false);
    expect(store.listingsLoading()).toBe(false);
    http.verify();
  });

  it('allows each section to recover after the home request fails', () => {
    TestBed.configureTestingModule({
      providers: [HomeStore, provideHttpClient(), provideHttpClientTesting()],
    });
    const store = TestBed.inject(HomeStore);
    const http = TestBed.inject(HttpTestingController);
    store.load();
    http.expectOne('/api/v1/home/').flush({}, { status: 503, statusText: 'Unavailable' });
    expect(store.categoriesLoading()).toBe(false);
    expect(store.listingsLoading()).toBe(false);
    expect(store.categoriesError()).toContain('try again');
    store.loadListings();
    http.expectOne('/api/v1/listings/').flush({ results: [listingFixture], count: 1 });
    expect(store.listings()[0].id).toBe(12);
    expect(store.listingsError()).toBe('');
    expect(store.categoriesError()).toContain('try again');
    store.loadCategories();
    http.expectOne('/api/v1/categories/').flush([]);
    expect(store.categoriesError()).toBe('');
    http.verify();
  });

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
