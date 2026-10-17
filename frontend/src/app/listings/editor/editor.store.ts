import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { Observable, exhaustMap, filter, forkJoin, of, pipe, switchMap, tap } from 'rxjs';
import { CategoryApi } from '@app/categories/browse/category-api';
import { CategoryData } from '@app/categories/category-types';
import { listingError } from '@app/listings/listing-errors';
import {
  ListingAudit,
  ListingDraft,
  ListingValues,
  ModerationCase,
} from '@app/listings/listing-types';
import { ListingEditorApi } from './listing-editor-api';
interface EditorState {
  listing: ListingDraft | null;
  categories: CategoryData[];
  cases: ModerationCase[];
  history: ListingAudit[];
  loading: boolean;
  pending: boolean;
  error: string;
  notice: string;
  conflict: boolean;
}
export type EditorMutation =
  | { kind: 'save'; id: number | null; values: ListingValues & { version?: number } }
  | { kind: 'submit'; id: number; version: number }
  | { kind: 'upload'; id: number; version: number; file: File }
  | { kind: 'images'; id: number; version: number; images: string[] }
  | { kind: 'appeal'; id: number; version: number; reason: string };
@Injectable()
export class EditorStore {
  private readonly state = signalState<EditorState>({
    listing: null,
    categories: [],
    cases: [],
    history: [],
    loading: false,
    pending: false,
    error: '',
    notice: '',
    conflict: false,
  });
  readonly listing = this.state.listing;
  readonly categories = this.state.categories;
  readonly cases = this.state.cases;
  readonly history = this.state.history;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly notice = this.state.notice;
  readonly conflict = this.state.conflict;
  constructor(
    private readonly api: ListingEditorApi,
    private readonly categoriesApi: CategoryApi,
  ) {}
  readonly load = rxMethod<number | null>(
    pipe(
      filter(() => !this.pending()),
      switchMap((id) => {
        patchState(this.state, { loading: true, error: '', notice: '', conflict: false });
        return forkJoin({
          categories: this.categoriesApi.list(),
          listing: id ? this.api.retrieve(id) : of(null),
          cases: id ? this.api.moderation(id) : of([]),
          history: id ? this.api.history(id) : of([]),
        }).pipe(
          tapResponse({
            next: (data) => patchState(this.state, data),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, { error: listingError(error) }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );
  readonly mutate = rxMethod<EditorMutation>(
    pipe(
      filter(() => !this.pending() && !this.loading() && !this.conflict()),
      tap(() => patchState(this.state, { pending: true, error: '', notice: '' })),
      exhaustMap((value) =>
        this.request(value).pipe(
          tapResponse({
            next: (listing) => this.finish(listing, value.kind),
            error: (error: HttpErrorResponse) =>
              patchState(this.state, {
                error: listingError(error),
                conflict: error.status === 409,
              }),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );
  readonly refreshHistory = rxMethod<number>(
    pipe(
      switchMap((id) =>
        forkJoin({ cases: this.api.moderation(id), history: this.api.history(id) }).pipe(
          tapResponse({
            next: (data) => patchState(this.state, data),
            error: () =>
              patchState(this.state, {
                error: 'Saved, but the review history could not be refreshed. Reload to try again.',
              }),
          }),
        ),
      ),
    ),
  );
  private request(value: EditorMutation): Observable<ListingDraft> {
    switch (value.kind) {
      case 'save':
        return this.api.save(value.id, value.values);
      case 'upload':
        return this.api.upload(value.id, value.version, value.file);
      case 'images':
        return this.api.images(value.id, value.version, value.images);
      case 'appeal':
        return this.api.appeal(value.id, value.version, value.reason);
      case 'submit':
        return this.api.submit(value.id, value.version);
    }
  }
  private finish(listing: ListingDraft, kind: EditorMutation['kind']): void {
    const notices: Record<EditorMutation['kind'], string> = {
      save: 'Draft saved.',
      upload: 'Image uploaded.',
      images: 'Images updated. The first image is the cover.',
      submit: 'Submitted for manual review. This draft is not published yet.',
      appeal: 'Appeal sent for another admin review.',
    };
    patchState(this.state, { listing, notice: notices[kind] });
    this.refreshHistory(listing.id);
  }
}
