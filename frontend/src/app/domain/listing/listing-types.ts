import { components } from '@app/data-access/generated/schema';
import { AttributeValues, CategoryData } from '@app/domain/category/category-types';

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
export interface ListingImage {
  id: string;
  url: string;
}
export type ListingStatus = components['schemas']['ListingStatusEnum'];
export interface ListingValues {
  title: string;
  description: string;
  category: string | null;
  condition: 'new' | 'used';
  price_mode: 'fixed' | 'negotiable' | 'free';
  price: number | null;
  area: string;
  attributes: AttributeValues;
  schema_version: number;
  phone_consent: boolean;
  rights_confirmed: boolean;
}
export interface ListingDraft extends Omit<Required<components['schemas']['ListingDraft']>,
  'attributes' | 'images' | 'published'> {
  attributes: AttributeValues;
  images: ListingImage[];
  published: Record<string, unknown>;
}
export interface PublicListing extends Omit<components['schemas']['ListingPublic'],
  'attributes' | 'category_schema'> {
  attributes: AttributeValues;
  category_schema: CategoryData;
}
export interface ListingSnapshot extends ListingValues {
  id: number;
  version: number;
  images: string[];
  category_schema?: CategoryData;
}
export interface ModerationCase extends Omit<components['schemas']['Moderation'], 'snapshot'> {
  snapshot: ListingSnapshot;
}
export type ListingAudit = Required<components['schemas']['ListingAudit']>;
export interface SearchFilters {
  q?: string;
  category?: string;
  shop?: string;
  location?: string;
  price_min?: number;
  price_max?: number;
  condition?: string;
  sort?: string;
  page?: number;
  attributes?: AttributeValues;
}
export function listingPrice(listing: { price: number | null; price_mode: string }): string {
  if (listing.price_mode === 'free') return 'Free';
  if (listing.price === null) return 'Contact for price';
  return (
    new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(listing.price) +
    (listing.price_mode === 'negotiable' ? ' · Negotiable' : '')
  );
}
