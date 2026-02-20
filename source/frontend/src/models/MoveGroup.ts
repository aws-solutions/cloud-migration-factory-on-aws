export type MoveGroup = {
  // System attributes
  move_group_id: string;
  move_group_name: string;

  // Relationships
  wpm_job_id?: string; // Relationship to wpm_job
  wave_id?: string; // Relationship to wave

  // Numeric values
  server_count: number;
  total_server_storage: number;
  complexity_score: number;

  // Multi-value relationships
  app_ids: string[]; // Relationship to multiple apps
  server_ids: string[]; // Relationship to multiple servers
  database_ids: string[]; // Relationship to multiple databases
};
