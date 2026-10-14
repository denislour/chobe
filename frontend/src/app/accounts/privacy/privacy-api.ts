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

@Injectable({ providedIn: 'root' })
export class PrivacyApi {
  constructor(private readonly http: HttpClient) {}

  privacy(): Observable<PrivacyData> {
    return this.http.get<PrivacyData>('/api/v1/me/privacy-settings/');
  }

  savePrivacy(
    values: Pick<PrivacyData, 'share_phone' | 'record_history' | 'version'>,
  ): Observable<PrivacyData> {
    return this.http.patch<PrivacyData>('/api/v1/me/privacy-settings/', values);
  }

  history(): Observable<HistoryEntry[]> {
    return this.http.get<HistoryEntry[]>('/api/v1/me/viewing-history/');
  }

  clearHistory(): Observable<void> {
    return this.http.delete<void>('/api/v1/me/viewing-history/');
  }
}
