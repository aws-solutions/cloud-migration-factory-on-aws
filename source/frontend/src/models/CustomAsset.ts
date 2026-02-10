export type CustomAsset = {
  [key: `${string}_id`]: string;
  [key: `${string}_name`]: string;
  app_ids?: string[];
  move_group_ids?: string[];
  wave_ids?: string[];
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
  [key: string]: unknown;
};
