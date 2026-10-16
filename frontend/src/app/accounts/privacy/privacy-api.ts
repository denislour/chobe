import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface PrivacyData {
  share_phone: boolean;
  record_history: boolean;
  consent_at: string | null;
  version: number;
  updated_at: string;
}

export interface HistoryEntry {
  listing_id: number;
  viewed_at: string;
}

export interface AccountDataExportJob {
  job_id: string;
  status: 'queued' | 'processing' | 'ready' | 'failed' | 'expired';
  created_at: string;
  expires_at: string | null;
}

export interface DeletionJob {
  job_id: string;
  status: 'requested' | 'processing' | 'completed' | 'failed';
  created_at: string;
  completed_at: string | null;
}

export interface DeletionCredentials {
  password: string;
  confirmation: string;
}

@Injectable({ providedIn: 'root' })
export class PrivacyApi {
  constructor(private readonly http: HttpClient) {}

  privacy(): Observable<PrivacyData> {
    return this.http.get<PrivacyData>('/api/v1/privacy-settings/me/');
  }

  savePrivacy(
    values: Pick<PrivacyData, 'share_phone' | 'record_history' | 'version'>,
  ): Observable<PrivacyData> {
    return this.http.patch<PrivacyData>('/api/v1/privacy-settings/me/', values);
  }

  history(): Observable<HistoryEntry[]> {
    return this.http.get<HistoryEntry[]>('/api/v1/me/viewing-history/');
  }

  clearHistory(): Observable<void> {
    return this.http.delete<void>('/api/v1/me/viewing-history/clear/');
  }

  accountDataExports(): Observable<AccountDataExportJob[]> {
    return this.http.get<AccountDataExportJob[]>('/api/v1/me/data-exports/');
  }

  createAccountDataExport(): Observable<AccountDataExportJob> {
    return this.http.post<AccountDataExportJob>('/api/v1/me/data-exports/', {});
  }

  deleteAccount(values: DeletionCredentials): Observable<DeletionJob & { receipt: string }> {
    return this.http.post<DeletionJob & { receipt: string }>(
      '/api/v1/me/deletion-requests/',
      values,
    );
  }

  deletionStatus(receipt: string): Observable<DeletionJob> {
    return this.http.get<DeletionJob>(
      `/api/v1/account-deletion-status/${encodeURIComponent(receipt)}/`,
    );
  }
}
