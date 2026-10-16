import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface ProfileData {
  display_name: string;
  username: string;
  email: string;
  area: string;
  bio: string;
  phone: string;
  avatar_url: string | null;
  version: number;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class ProfileApi {
  constructor(private readonly http: HttpClient) {}

  profile(): Observable<ProfileData> {
    return this.http.get<ProfileData>('/api/v1/profiles/me/');
  }

  saveProfile(values: FormData): Observable<ProfileData> {
    return this.http.patch<ProfileData>('/api/v1/profiles/me/', values);
  }
}
