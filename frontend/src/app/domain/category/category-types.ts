import { components } from '@app/data-access/generated/schema';

export type AttributeValue = string | number | boolean | null;
export type AttributeValues = Record<string, AttributeValue>;
export type AttributeType = components['schemas']['TypeEnum'];
export type AttributeDefinition = Required<components['schemas']['AttributeDefinition']>;

export interface CategoryData extends Omit<components['schemas']['Category'], 'attributes'> {
  attributes: AttributeDefinition[];
}

export interface CategoryFacets extends Omit<components['schemas']['CategoryFacets'], 'fields'> {
  fields: AttributeDefinition[];
}

export interface ValidatedCategoryValues {
  category_id: string;
  version: number;
  attributes: AttributeValues;
}
