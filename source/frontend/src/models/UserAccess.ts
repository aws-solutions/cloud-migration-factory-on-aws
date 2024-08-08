export type SchemaAccess = Record<string, boolean>;

/**
 * this type is used to determine whether to allow add/edit/delete in the UI,
 */
export type ActionDenyType = {
  add?: boolean;
  edit?: boolean;
  delete?: boolean;
};

export const defaultAllDeny: ActionDenyType = {
  add: true,
  edit: true,
  delete: true,
};

/**
 * this type is used when reading from and saving to the backend
 */
export type EntityAccessRecord = {
  attributes?: any[];
  read?: boolean;
  create?: boolean;
  delete?: boolean;
  update?: boolean;
};

export type UserAccess = Record<string, EntityAccessRecord>;
