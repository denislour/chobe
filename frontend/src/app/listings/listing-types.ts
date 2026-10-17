import { AttributeValues, CategoryData } from '@app/categories/category-types';

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
export type ListingStatus =
  'draft' | 'pending' | 'rejected' | 'active' | 'hidden' | 'sold' | 'deleted';
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
export interface ListingDraft extends ListingValues {
  id: number;
  status: ListingStatus;
  version: number;
  submitted_version: number | null;
  moderation_hold: boolean;
  published: Record<string, unknown>;
  images: ListingImage[];
  retention_due_at: string;
  last_owner_action_at: string;
  created_at: string;
  updated_at: string;
}
export interface PublicListing extends Omit<ListingValues, 'phone_consent' | 'rights_confirmed'> {
  id: number;
  version: number;
  images: ListingImage[];
  published_at: string;
  category_schema: CategoryData;
  shop: { id: string; name: string; slug: string };
  phone: string | null;
  is_favorite: boolean;
}
export interface ListingSnapshot extends ListingValues {
  id: number;
  version: number;
  images: string[];
  category_schema?: CategoryData;
}
export interface ModerationCase {
  id: number;
  listing_id: number;
  listing_version: number;
  snapshot: ListingSnapshot;
  current: boolean;
  status: 'pending' | 'approved' | 'rejected';
  source: string;
  reason: string;
  appeal: string;
  appeal_open: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}
export interface ListingAudit {
  id: number;
  actor_id: number | null;
  action: string;
  source: string;
  version: number;
  reason: string;
  created_at: string;
}
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
