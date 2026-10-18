import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tapResponse } from '@ngrx/operators';
import { patchState, signalState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { exhaustMap, filter, forkJoin, of, pipe, switchMap, tap } from 'rxjs';
import { AttributeValues, CategoryData, CategoryFacets } from './category-types';
import { CategoryApi } from '@app/data-access/categories/category-api';

interface CategoryState {
  categories: CategoryData[];
  category: CategoryData | null;
  facets: CategoryFacets | null;
  loading: boolean;
  pending: boolean;
  error: string;
  validationError: string;
  fieldErrors: Record<string, string[]>;
  notice: string;
}

interface AttributeCheck {
  id: string;
  version: number;
  attributes: AttributeValues;
}

@Injectable()
export class CategoryStore {
  private readonly state = signalState<CategoryState>({
    categories: [],
    category: null,
    facets: null,
    loading: false,
    pending: false,
    error: '',
    validationError: '',
    fieldErrors: {},
    notice: '',
  });
  readonly categories = this.state.categories;
  readonly category = this.state.category;
  readonly facets = this.state.facets;
  readonly loading = this.state.loading;
  readonly pending = this.state.pending;
  readonly error = this.state.error;
  readonly validationError = this.state.validationError;
  readonly fieldErrors = this.state.fieldErrors;
  readonly notice = this.state.notice;

  constructor(private readonly api: CategoryApi) {}

  readonly load = rxMethod<string | null>(
    pipe(
      switchMap((id) => {
        patchState(this.state, {
          loading: true,
          category: null,
          facets: null,
          error: '',
          validationError: '',
          fieldErrors: {},
          notice: '',
        });
        return forkJoin({
          categories: this.api.list(),
          category: id ? this.api.retrieve(id) : of(null),
          facets: id ? this.api.facets(id) : of(null),
        }).pipe(
          tapResponse({
            next: ({ categories, category, facets }) => {
              if (category && facets && category.version !== facets.version) {
                patchState(this.state, {
                  error: 'This category changed while loading. Please reload its fields.',
                });
                return;
              }
              patchState(this.state, { categories, category, facets });
            },
            error: (error: HttpErrorResponse) =>
              patchState(this.state, {
                categories: [],
                error:
                  error.status === 404
                    ? 'This category is not available. Choose another category.'
                    : 'Unable to load categories. Please try again.',
              }),
            finalize: () => patchState(this.state, { loading: false }),
          }),
        );
      }),
    ),
  );

  readonly validate = rxMethod<AttributeCheck>(
    pipe(
      filter(
        (check) =>
          !this.pending() &&
          !this.loading() &&
          this.category()?.id === check.id &&
          this.category()?.version === check.version,
      ),
      tap(() =>
        patchState(this.state, { pending: true, validationError: '', fieldErrors: {}, notice: '' }),
      ),
      exhaustMap((check) =>
        this.api.validate(check.id, check.version, check.attributes).pipe(
          tapResponse({
            next: () => {
              if (this.category()?.id === check.id && this.category()?.version === check.version) {
                patchState(this.state, {
                  notice: 'These attributes match the current category schema.',
                });
              }
            },
            error: (error: HttpErrorResponse) => {
              if (this.category()?.id !== check.id || this.category()?.version !== check.version)
                return;
              patchState(this.state, {
                validationError:
                  error.status === 409
                    ? 'This category has changed. Reload its fields and review your values.'
                    : error.status === 404
                      ? 'This category is no longer available. Choose another category.'
                      : 'Check the highlighted fields and try again.',
                fieldErrors: error.error?.attributes ?? {},
              });
            },
            finalize: () => patchState(this.state, { pending: false }),
          }),
        ),
      ),
    ),
  );

  clearValidation(): void {
    patchState(this.state, { validationError: '', fieldErrors: {}, notice: '' });
  }
}
