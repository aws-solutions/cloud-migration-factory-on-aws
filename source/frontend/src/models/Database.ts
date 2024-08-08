export type Database = {
  app_id: string;
  database_type: string;
  database_id: string;
  database_name: string;
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
