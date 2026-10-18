import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Page, SearchFilters } from '@app/domain/listing/listing-types';
export interface SavedSearchValues {
  name: string;
  filters: SearchFilters;
  active: boolean;
  frequency: 'daily' | 'immediate';
  version?: number;
}
export interface SavedSearch extends SavedSearchValues {
  id: number;
  version: number;
  created_at: string;
}
export interface NotificationItem {
  id: number;
  listing_id: number;
  title: string;
  available: boolean;
  search_name: string;
  read_at: string | null;
  email_status: string;
  created_at: string;
}
export interface NotificationPreferences {
  inbox: boolean;
  email: boolean;
  version: number;
}
@Injectable({ providedIn: 'root' })
export class AlertsApi {
  constructor(private readonly http: HttpClient) {}
  searches(page = 1): Observable<Page<SavedSearch>> {
    return this.http.get<Page<SavedSearch>>('/api/v1/me/saved-searches/', { params: { page } });
  }
  save(id: number | null, values: SavedSearchValues): Observable<SavedSearch> {
    return id
      ? this.http.patch<SavedSearch>(`/api/v1/me/saved-searches/${id}/`, values)
      : this.http.post<SavedSearch>('/api/v1/me/saved-searches/', values);
  }
  remove(id: number): Observable<void> {
    return this.http.delete<void>(`/api/v1/me/saved-searches/${id}/`);
  }
  notifications(page = 1): Observable<Page<NotificationItem>> {
    return this.http.get<Page<NotificationItem>>('/api/v1/me/notifications/', { params: { page } });
  }
  read(id: number): Observable<NotificationItem> {
    return this.http.post<NotificationItem>(`/api/v1/me/notifications/${id}/read/`, {});
  }
  readAll(): Observable<void> {
    return this.http.post<void>('/api/v1/me/notifications/read-all/', {});
  }
  preferences(): Observable<NotificationPreferences> {
    return this.http.get<NotificationPreferences>('/api/v1/me/notification-preferences/me/');
  }
  savePreferences(values: NotificationPreferences): Observable<NotificationPreferences> {
    return this.http.patch<NotificationPreferences>(
      '/api/v1/me/notification-preferences/me/',
      values,
    );
  }
}
