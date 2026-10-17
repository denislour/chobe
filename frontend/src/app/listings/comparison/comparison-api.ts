import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { PublicListing } from '@app/listings/listing-types';
export interface ComparisonResult {
  results: PublicListing[];
  unavailable: number[];
}
@Injectable({ providedIn: 'root' })
export class ComparisonApi {
  constructor(private readonly http: HttpClient) {}
  compare(ids: string): Observable<ComparisonResult> {
    return this.http.get<ComparisonResult>('/api/v1/listings/compare/', { params: { ids } });
  }
}
