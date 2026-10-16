import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface StorefrontData {
  id: string;
  name: string;
  slug: string;
  description: string;
  area: string;
  contact_hours: string;
  website_url: string;
  social_url: string;
  logo_url: string | null;
  banner_url: string | null;
  created_at: string;
  is_following: boolean;
}

@Injectable({ providedIn: 'root' })
export class StorefrontApi {
  constructor(private readonly http: HttpClient) {}

  retrieve(slug: string): Observable<StorefrontData> {
    return this.http.get<StorefrontData>(
      `/api/v1/shop-storefronts/${encodeURIComponent(slug)}/`,
    );
  }
}
