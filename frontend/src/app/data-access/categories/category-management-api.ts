import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { AttributeDefinition, CategoryData } from '@app/domain/category/category-types';

export interface CategoryDraft {
  id: string;
  name: string;
  slug: string;
  description: string;
  parent: string | null;
  sort_order: number;
  restricted: boolean;
  attributes: AttributeDefinition[];
  version: number;
  status: 'draft' | 'active' | 'retired';
  published: CategoryData | Record<string, never>;
  updated_at: string;
}

export interface CategoryDraftValues {
  name: string;
  slug: string;
  description: string;
  parent: string | null;
  sort_order: number;
  restricted: boolean;
  attributes: AttributeDefinition[];
  version?: number;
}

export interface TaxonomyCapabilities {
  create: boolean;
  edit: boolean;
  publish: boolean;
  retire: boolean;
}

export interface CategoryRevision {
  version: number;
  snapshot: CategoryData;
  created_at: string;
}

export interface CategoryAuditEvent {
  id: string;
  actor_id: number | null;
  action: string;
  version: number;
  created_at: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class CategoryManagementApi {
  constructor(private readonly http: HttpClient) {}

  list(): Observable<CategoryDraft[]> {
    return this.http.get<CategoryDraft[]>('/api/v1/admin/categories/');
  }

  capabilities(): Observable<TaxonomyCapabilities> {
    return this.http.get<TaxonomyCapabilities>('/api/v1/admin/categories/capabilities/');
  }

  retrieve(id: string): Observable<CategoryDraft> {
    return this.http.get<CategoryDraft>(`/api/v1/admin/categories/${encodeURIComponent(id)}/`);
  }

  revisions(id: string): Observable<CategoryRevision[]> {
    return this.http.get<CategoryRevision[]>(
      `/api/v1/admin/categories/${encodeURIComponent(id)}/revisions/`,
    );
  }

  history(id: string): Observable<CategoryAuditEvent[]> {
    return this.http.get<CategoryAuditEvent[]>(
      `/api/v1/admin/categories/${encodeURIComponent(id)}/history/`,
    );
  }

  save(id: string | null, values: CategoryDraftValues): Observable<CategoryDraft> {
    return id
      ? this.http.patch<CategoryDraft>(
          `/api/v1/admin/categories/${encodeURIComponent(id)}/`,
          values,
        )
      : this.http.post<CategoryDraft>('/api/v1/admin/categories/', values);
  }

  transition(id: string, action: 'publish' | 'retire', version: number): Observable<CategoryDraft> {
    return this.http.post<CategoryDraft>(
      `/api/v1/admin/categories/${encodeURIComponent(id)}/${action}/`,
      { version },
    );
  }
}
