import { CategoryData } from './category-types';
import {
  CategoryDraft,
  TaxonomyCapabilities,
} from '@app/categories/management/category-management-api';

export const categoryFixture: CategoryData = {
  id: '22222222-2222-4222-8222-222222222222',
  name: 'Electronics',
  slug: 'electronics',
  description: 'Devices and accessories.',
  parent: null,
  sort_order: 0,
  version: 2,
  attributes: [
    {
      key: 'storage_gb',
      label: 'Storage',
      type: 'integer',
      unit: 'GB',
      min_value: 1,
      max_value: 2048,
      max_length: 200,
      required: true,
      filterable: true,
      choices: [],
    },
    {
      key: 'tested',
      label: 'Tested',
      type: 'boolean',
      unit: '',
      min_value: null,
      max_value: null,
      max_length: 200,
      required: true,
      filterable: false,
      choices: [],
    },
  ],
};

export const categoryDraftFixture: CategoryDraft = {
  ...categoryFixture,
  restricted: false,
  status: 'active',
  published: categoryFixture,
  updated_at: '2026-10-16T00:00:00Z',
};

export const taxonomyCapabilitiesFixture: TaxonomyCapabilities = {
  create: true,
  edit: true,
  publish: true,
  retire: true,
};
