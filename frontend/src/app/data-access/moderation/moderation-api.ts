import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ListingAudit, ModerationCase, Page } from '@app/domain/listing/listing-types';
@Injectable({ providedIn: 'root' })
export class ModerationApi {
  constructor(private readonly http: HttpClient) {}
  list(status: string, appeals: boolean, page: number): Observable<Page<ModerationCase>> {
    return this.http.get<Page<ModerationCase>>('/api/v1/admin/moderation/', {
      params: { status, appeals: String(appeals), page },
    });
  }
  retrieve(id: number): Observable<ModerationCase> {
    return this.http.get<ModerationCase>(`/api/v1/admin/moderation/${id}/`);
  }
  history(id: number): Observable<ListingAudit[]> {
    return this.http.get<ListingAudit[]>(`/api/v1/admin/moderation/${id}/history/`);
  }
  decision(
    id: number,
    version: number,
    decision: 'approve' | 'reject',
    reason: string,
  ): Observable<ModerationCase> {
    return this.http.post<ModerationCase>(`/api/v1/admin/moderation/${id}/decision/`, {
      version,
      decision,
      reason,
    });
  }
}
