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
}
