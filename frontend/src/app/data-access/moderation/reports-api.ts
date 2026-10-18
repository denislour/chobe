import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { components } from '@app/data-access/generated/schema';
import { Page } from '@app/domain/listing/listing-types';
export interface ReportValues {
  listing?: number;
  shop?: string;
  reason: string;
  description: string;
}
export type ReportRecord = Required<components['schemas']['Report']>;
export type ReportDecisionValues = components['schemas']['ReportDecision'];
export type ReportAudit = components['schemas']['ReportAudit'];
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
