import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Page, PublicListing } from '@app/listings/listing-types';
@Injectable({ providedIn: 'root' })
export class LibraryApi {
  constructor(private readonly http: HttpClient) {}
  favorites(page = 1): Observable<Page<PublicListing>> {
    return this.http.get<Page<PublicListing>>('/api/v1/me/favorites/', { params: { page } });
  }
  history(): Observable<PublicListing[]> {
    return this.http.get<PublicListing[]>('/api/v1/me/favorites/history/');
  }
  favorite(id: number, saved: boolean): Observable<void> {
    const url = `/api/v1/me/favorites/${id}/`;
    return saved ? this.http.put<void>(url, {}) : this.http.delete<void>(url);
  }
  clearHistory(): Observable<void> {
    return this.http.delete<void>('/api/v1/me/viewing-history/clear/');
  }
}
