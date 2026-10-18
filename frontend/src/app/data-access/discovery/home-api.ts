import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { components } from '@app/data-access/generated/schema';
import { CategoryData } from '@app/domain/category/category-types';
import { PublicListing } from '@app/domain/listing/listing-types';

export interface HomePayload extends Omit<components['schemas']['HomePayload'], 'categories' | 'latest'> {
  categories: CategoryData[];
  latest: PublicListing[];
}

@Injectable({ providedIn: 'root' })
export class HomeApi {
  constructor(private readonly http: HttpClient) {}

  load(): Observable<HomePayload> {
    return this.http.get<HomePayload>('/api/v1/home/');
  }
}
