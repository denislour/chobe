import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { categoryFixture } from '@app/domain/category/category-fixtures';
import { draftFixture } from '@app/listings/listing-fixtures';
import { EditorStore } from './editor.store';
describe('EditorStore', () => {
  let store: EditorStore;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [EditorStore, provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(EditorStore);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  function load(): void {
    store.load(12);
    http.expectOne('/api/v1/categories/').flush([categoryFixture]);
    http.expectOne('/api/v1/me/listings/12/').flush(draftFixture);
    http.expectOne('/api/v1/me/listings/12/moderation/').flush([]);
    http.expectOne('/api/v1/me/listings/12/history/').flush([]);
  }
  it('loads the saved draft and retains it when a save conflicts', () => {
    load();
    store.mutate({ kind: 'save', id: 12, values: draftFixture });
    store.mutate({ kind: 'save', id: 12, values: draftFixture });
    http.expectOne('/api/v1/me/listings/12/').flush({}, { status: 409, statusText: 'Conflict' });
    expect(store.listing()?.title).toBe(draftFixture.title);
    expect(store.conflict()).toBe(true);
    expect(store.pending()).toBe(false);
    store.mutate({ kind: 'submit', id: 12, version: 4 });
    http.expectNone('/api/v1/me/listings/12/submit/');
  });
  it('sends the current version and refreshes review history after submit', () => {
    load();
    store.mutate({ kind: 'submit', id: 12, version: 4 });
    const request = http.expectOne('/api/v1/me/listings/12/submit/');
    expect(request.request.body).toEqual({ version: 4 });
    request.flush({ ...draftFixture, status: 'pending', version: 5 });
    http.expectOne('/api/v1/me/listings/12/moderation/').flush([]);
    http.expectOne('/api/v1/me/listings/12/history/').flush([]);
    expect(store.notice()).toContain('manual review');
    expect(store.listing()?.version).toBe(5);
  });
  it('uploads the actual file and version as multipart data', () => {
    load();
    const file = new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' });
    store.mutate({ kind: 'upload', id: 12, version: 4, file });
    const request = http.expectOne('/api/v1/me/listings/12/images/');
    expect(request.request.body.get('version')).toBe('4');
    expect(request.request.body.get('image')).toBe(file);
    request.flush({ image: ['Invalid image.'] }, { status: 400, statusText: 'Bad Request' });
    expect(store.error()).toContain('Invalid image');
    expect(store.pending()).toBe(false);
  });
});
