import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  AttributeValues,
  CategoryData,
  CategoryFacets,
  ValidatedCategoryValues,
} from '@app/domain/category/category-types';

@Injectable({ providedIn: 'root' })
export class CategoryApi {
  constructor(private readonly http: HttpClient) {}

  list(): Observable<CategoryData[]> {
    return this.http.get<CategoryData[]>('/api/v1/categories/');
  }

  retrieve(id: string): Observable<CategoryData> {
    return this.http.get<CategoryData>(`/api/v1/categories/${encodeURIComponent(id)}/`);
  }

  facets(id: string): Observable<CategoryFacets> {
    return this.http.get<CategoryFacets>(`/api/v1/categories/${encodeURIComponent(id)}/facets/`);
  }

  validate(
    id: string,
    version: number,
    attributes: AttributeValues,
  ): Observable<ValidatedCategoryValues> {
    return this.http.post<ValidatedCategoryValues>(
      `/api/v1/categories/${encodeURIComponent(id)}/validate-attributes/`,
      { version, attributes },
    );
  }
}
