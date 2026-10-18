import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, forkJoin, pipe, switchMap, tap } from 'rxjs';
import {
  CategoryAuditEvent,
  CategoryDraft,
  CategoryDraftValues,
  CategoryManagementApi,
  CategoryRevision,
  TaxonomyCapabilities,
} from '@app/data-access/categories/category-management-api';

interface ManagementState {
  categories: CategoryDraft[];
  draft: CategoryDraft | null;
  revisions: CategoryRevision[];
  history: CategoryAuditEvent[];
  capabilities: TaxonomyCapabilities | null;
  loading: boolean;
  selecting: boolean;
  pending: boolean;
  error: string;
  fieldErrors: Record<string, unknown>;
  notice: string;
}

@Injectable()
export class CategoryManagementStore {
  private readonly state = signalState<ManagementState>({
    categories: [],
    draft: null,
    revisions: [],
    history: [],
    capabilities: null,
    loading: false,
    selecting: false,
    pending: false,
    error: '',
    fieldErrors: {},
    notice: '',
  });
  readonly categories = this.state.categories;
  readonly draft = this.state.draft;
  readonly revisions = this.state.revisions;
  readonly history = this.state.history;
  readonly capabilities = this.state.capabilities;
  readonly loading = this.state.loading;
  readonly selecting = this.state.selecting;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly fieldErrors = this.state.fieldErrors;
  readonly notice = this.state.notice;

  constructor(private readonly api: CategoryManagementApi) {}

  readonly load = rxMethod<void>(
    pipe(
      filter(() => !this.pending() && !this.selecting()),
      switchMap(() => {
        patchState(this.state, { loading: true, error: '', capabilities: null });
        return forkJoin({
          categories: this.api.list(),
          capabilities: this.api.capabilities(),
        }).pipe(
          tapResponse({
            next: ({ categories, capabilities }) =>
              patchState(this.state, { categories, capabilities }),
            error: (error: HttpErrorResponse) => this.fail(error),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );

  readonly select = rxMethod<string>(
    pipe(
      filter(() => !this.pending()),
      switchMap((id) => {
        patchState(this.state, { selecting: true, error: '', notice: '', fieldErrors: {} });
        return forkJoin({
          draft: this.api.retrieve(id),
          revisions: this.api.revisions(id),
          history: this.api.history(id),
        }).pipe(
          tapResponse({
            next: ({ draft, revisions, history }) =>
              patchState(this.state, { draft, revisions, history }),
            error: (error: HttpErrorResponse) => this.fail(error),
            finalize: () => patchState(this.state, { selecting: false }),
          }),
        );
      }),
    ),
  );

  readonly save = rxMethod<{ id: string | null; values: CategoryDraftValues }>(
    pipe(
      filter(() => !this.pending() && !this.selecting() && !this.loading()),
      tap(() => patchState(this.state, { pending: true, error: '', fieldErrors: {}, notice: '' })),
      exhaustMap(({ id, values }) =>
        this.api.save(id, values).pipe(
          tapResponse({
            next: (draft) =>
              this.finish(draft, 'Draft saved. Public category details have not changed.'),
            error: (error: HttpErrorResponse) => this.fail(error),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  readonly transition = rxMethod<{ id: string; version: number; action: 'publish' | 'retire' }>(
    pipe(
      filter(() => !this.pending() && !this.selecting() && !this.loading()),
      tap(() => patchState(this.state, { pending: true, error: '', fieldErrors: {}, notice: '' })),
      exhaustMap(({ id, version, action }) =>
        this.api.transition(id, action, version).pipe(
          tapResponse({
            next: (draft) =>
              this.finish(
                draft,
                action === 'publish' ? 'Category version published.' : 'Category retired.',
              ),
            error: (error: HttpErrorResponse) => this.fail(error),
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  newDraft(): void {
    if (this.pending() || this.selecting()) return;
    patchState(this.state, {
      draft: null,
      revisions: [],
      history: [],
      error: '',
      fieldErrors: {},
      notice: '',
    });
  }

  private finish(draft: CategoryDraft, notice: string): void {
    const categories = this.categories().filter((item) => item.id !== draft.id);
    patchState(this.state, { draft, categories: [...categories, draft], notice, pending: false });
    this.select(draft.id);
    patchState(this.state, { notice });
  }

  private fail(error: HttpErrorResponse): void {
    const messages: Record<number, string> = {
      403: 'You do not have permission for this action. If your session expired, log in again.',
      404: 'This category is no longer available. Reload the category list.',
      409: 'This category changed in another session. Your input is kept; reload the draft before saving again.',
      429: 'Too many changes. Please wait a moment and try again.',
    };
    patchState(this.state, {
      error:
        messages[error.status] ??
        'Unable to save or load this category. Review the errors and try again.',
      fieldErrors: error.status === 400 ? error.error : {},
    });
  }
}
