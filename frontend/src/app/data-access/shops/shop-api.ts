import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export type ShopStatus = 'active' | 'paused' | 'suspended' | 'closed';
export type OwnerShopStatus = Exclude<ShopStatus, 'suspended'>;

export interface ShopDisplayData {
  name: string;
  slug: string;
  description: string;
  area: string;
  contact_hours: string;
  website_url: string;
  social_url: string;
  logo_url: string | null;
  banner_url: string | null;
  status: ShopStatus;
}

export interface ShopData extends ShopDisplayData {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ShopSaveRequest {
  id: string | null;
  body: FormData;
}

export interface ShopStatusRequest {
  id: string;
  status: OwnerShopStatus;
  version: number;
}

@Injectable({ providedIn: 'root' })
export class ShopApi {
  constructor(private readonly http: HttpClient) {}

  mine(): Observable<ShopData> {
    return this.http.get<ShopData>('/api/v1/shops/mine/');
  }

  save({ id, body }: ShopSaveRequest): Observable<ShopData> {
    return id
      ? this.http.patch<ShopData>(`/api/v1/shops/${encodeURIComponent(id)}/`, body)
      : this.http.post<ShopData>('/api/v1/shops/', body);
  }

  changeStatus({ id, status, version }: ShopStatusRequest): Observable<ShopData> {
    return this.http.post<ShopData>(
      `/api/v1/shops/${encodeURIComponent(id)}/status/`,
      { status, version },
    );
  }

  preview(slug: string): Observable<ShopData> {
    return this.http.get<ShopData>(`/api/v1/shops/${encodeURIComponent(slug)}/preview/`);
  }
}
