export type EntityAccess = {
  attributes?: any[];
  add?: boolean;
  edit?: boolean;
  create?: boolean;
  delete?: boolean;
  update?: boolean;
};
export type UserAccess = Record<string, EntityAccess>;
export type SchemaAccess = Record<string, boolean>;