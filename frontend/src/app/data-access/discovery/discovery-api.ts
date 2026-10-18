import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Page, PublicListing, SearchFilters } from '@app/domain/listing/listing-types';
@Injectable({ providedIn: 'root' })
export class DiscoveryApi {
  constructor(private readonly http: HttpClient) {}
  list(filters: SearchFilters): Observable<Page<PublicListing>> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && value !== '')
        params = params.set(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
    }
    return this.http.get<Page<PublicListing>>('/api/v1/listings/', { params });
  }
  retrieve(id: number): Observable<PublicListing> {
    return this.http.get<PublicListing>(`/api/v1/listings/${id}/`);
  }
  recordView(id: number): Observable<unknown> {
    return this.http.post('/api/v1/me/viewing-history/', { listing_id: id });
  }
  event(id: number, kind: 'call' | 'copy'): Observable<void> {
    return this.http.post<void>(`/api/v1/listings/${id}/events/`, { kind });
  }
}
