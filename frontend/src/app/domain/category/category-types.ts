export type AttributeValue = string | number | boolean | null;
export type AttributeValues = Record<string, AttributeValue>;
export type AttributeType = 'text' | 'integer' | 'number' | 'boolean' | 'select';

export interface AttributeDefinition {
  key: string;
  label: string;
  type: AttributeType;
  required: boolean;
  filterable: boolean;
  unit: string;
  choices: { value: string; label: string }[];
  min_value: number | null;
  max_value: number | null;
  max_length: number;
}

export interface CategoryData {
  id: string;
  name: string;
  slug: string;
  description: string;
  parent: string | null;
  sort_order: number;
  version: number;
  attributes: AttributeDefinition[];
}

export interface CategoryFacets {
  category_id: string;
  version: number;
  fields: AttributeDefinition[];
}

export interface ValidatedCategoryValues {
  category_id: string;
  version: number;
  attributes: AttributeValues;
}
