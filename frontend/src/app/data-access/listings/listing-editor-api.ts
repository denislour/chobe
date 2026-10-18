import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  ListingAudit,
  ListingDraft,
  ListingValues,
  ModerationCase,
} from '@app/domain/listing/listing-types';
@Injectable({ providedIn: 'root' })
export class ListingEditorApi {
  constructor(private readonly http: HttpClient) {}
  retrieve(id: number): Observable<ListingDraft> {
    return this.http.get<ListingDraft>(`/api/v1/me/listings/${id}/`);
  }
  save(id: number | null, values: ListingValues & { version?: number }): Observable<ListingDraft> {
    return id
      ? this.http.patch<ListingDraft>(`/api/v1/me/listings/${id}/`, values)
      : this.http.post<ListingDraft>('/api/v1/me/listings/', values);
  }
  submit(id: number, version: number): Observable<ListingDraft> {
    return this.http.post<ListingDraft>(`/api/v1/me/listings/${id}/submit/`, { version });
  }
  upload(id: number, version: number, file: File): Observable<ListingDraft> {
    const data = new FormData();
    data.set('version', String(version));
    data.set('image', file);
    return this.http.post<ListingDraft>(`/api/v1/me/listings/${id}/images/`, data);
  }
  images(id: number, version: number, images: string[]): Observable<ListingDraft> {
    return this.http.post<ListingDraft>(`/api/v1/me/listings/${id}/images/order/`, {
      version,
      images,
    });
  }
  moderation(id: number): Observable<ModerationCase[]> {
    return this.http.get<ModerationCase[]>(`/api/v1/me/listings/${id}/moderation/`);
  }
  history(id: number): Observable<ListingAudit[]> {
    return this.http.get<ListingAudit[]>(`/api/v1/me/listings/${id}/history/`);
  }
  appeal(id: number, version: number, reason: string): Observable<ListingDraft> {
    return this.http.post<ListingDraft>(`/api/v1/me/listings/${id}/appeal/`, { version, reason });
  }
}
