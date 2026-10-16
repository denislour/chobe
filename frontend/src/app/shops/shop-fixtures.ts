import { StorefrontData } from '@app/shops/shop-storefront/storefront-api';
import { ShopData } from './shop-api';

export const shopFixture: ShopData = {
  id: '11111111-1111-4111-8111-111111111111',
  name: 'Moc Home',
  slug: 'moc-home',
  description: 'Furniture with a second life.',
  area: 'Ha Noi',
  contact_hours: '09:00–18:00',
  website_url: '',
  social_url: '',
  logo_url: null,
  banner_url: null,
  status: 'active',
  version: 1,
  created_at: '2026-10-15T00:00:00Z',
  updated_at: '2026-10-15T00:00:00Z',
};

export const storefrontFixture: StorefrontData = {
  id: shopFixture.id,
  name: shopFixture.name,
  slug: shopFixture.slug,
  description: shopFixture.description,
  area: shopFixture.area,
  contact_hours: shopFixture.contact_hours,
  website_url: '',
  social_url: '',
  logo_url: null,
  banner_url: null,
  created_at: shopFixture.created_at,
  is_following: false,
};
