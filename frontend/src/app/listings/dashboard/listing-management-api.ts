import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ListingDraft, Page } from '@app/listings/listing-types';
export interface OwnerFilters {
  state: string;
  q: string;
  page: number;
  retention: string;
}
@Injectable({ providedIn: 'root' })
export class ListingManagementApi {
  constructor(private readonly http: HttpClient) {}
  list(filters: OwnerFilters): Observable<Page<ListingDraft>> {
    const params: Record<string, string> = { page: String(filters.page) };
    for (const key of ['q', 'state', 'retention'] as const)
      if (filters[key]) params[key] = filters[key];
    return this.http.get<Page<ListingDraft>>('/api/v1/me/listings/', { params });
  }
  summary(): Observable<Record<string, number>> {
    return this.http.get<Record<string, number>>('/api/v1/me/listings/summary/');
  }
  status(id: number, version: number, status: string): Observable<ListingDraft> {
    return this.http.post<ListingDraft>(`/api/v1/me/listings/${id}/status/`, { version, status });
  }
  renew(id: number, version: number): Observable<ListingDraft> {
    return this.http.post<ListingDraft>(`/api/v1/me/listings/${id}/renew/`, { version });
  }
  remove(id: number, version: number): Observable<void> {
    return this.http.delete<void>(`/api/v1/me/listings/${id}/`, { body: { version } });
  }
}
