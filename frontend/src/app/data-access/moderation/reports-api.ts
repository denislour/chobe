import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Page } from '@app/listings/listing-types';
export interface ReportValues {
  listing?: number;
  shop?: string;
  reason: string;
  description: string;
}
export interface ReportRecord {
  id: string;
  listing: number | null;
  shop: string | null;
  reason: string;
  description: string;
  status: string;
  response: string;
  version: number;
  created_at: string;
}
export interface ReportDecisionValues {
  version: number;
  action: 'review' | 'dismiss' | 'resolve' | 'hide_listing' | 'suspend_shop';
  reason: string;
  response: string;
}
export interface ReportAudit {
  id: number;
  actor_id: number | null;
  action: string;
  reason: string;
  created_at: string;
}
@Injectable({ providedIn: 'root' })
export class ReportsApi {
  constructor(private readonly http: HttpClient) {}
  create(values: ReportValues): Observable<ReportRecord> {
    return this.http.post<ReportRecord>('/api/v1/me/reports/', values);
  }
  list(admin: boolean, page: number, status: string): Observable<Page<ReportRecord>> {
    return this.http.get<Page<ReportRecord>>(
      admin ? '/api/v1/admin/reports/' : '/api/v1/me/reports/',
      { params: { page, status } },
    );
  }
  decision(id: string, values: ReportDecisionValues): Observable<ReportRecord> {
    return this.http.post<ReportRecord>(
      `/api/v1/admin/reports/${encodeURIComponent(id)}/decision/`,
      values,
    );
  }
  history(id: string): Observable<ReportAudit[]> {
    return this.http.get<ReportAudit[]>(`/api/v1/admin/reports/${encodeURIComponent(id)}/history/`);
  }
}
