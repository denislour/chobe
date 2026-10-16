import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { StorefrontData } from '@app/shops/shop-storefront/storefront-api';

export interface FollowedShopsPage {
  count: number;
  next: string | null;
  previous: string | null;
  results: StorefrontData[];
}

@Injectable({ providedIn: 'root' })
export class FollowedShopsApi {
  constructor(private readonly http: HttpClient) {}

  list(page: number): Observable<FollowedShopsPage> {
    return this.http.get<FollowedShopsPage>('/api/v1/me/followed-shops/', {
      params: { page },
    });
  }

  setFollowing(id: string, following: boolean): Observable<void> {
    const url = `/api/v1/me/followed-shops/${encodeURIComponent(id)}/`;
    return following ? this.http.put<void>(url, {}) : this.http.delete<void>(url);
  }
}
