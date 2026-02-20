/**
 * Interface for Move Group Request entity
 */
export type MoveGroupRequest = {
  move_group_request_id: string;
  move_group_request_name: string;
  app_ids: string[];
  move_group_ids?: string[];
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  wpm_job_id: string;
  errorMessage?: string;
};
