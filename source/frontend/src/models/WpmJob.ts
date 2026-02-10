import { Application, Database, DataLoadingState, MoveGroup, Server, Wave } from ".";

export type WPMJobStep = "JOB_DETAILS" | "MANAGE_APPLICATIONS" | "MANAGE_MOVE_GROUPS" | "MANAGE_WAVES";

/**
 * Interface for WPM Job entity
 */
export type WPMJob = {
  wpm_job_id?: string;
  wpm_job_name: string;
  current_step: WPMJobStep;
  created_at?: string;
  updated_at?: string;
  description?: string;
  nomination_app_count?: number;
  wave_server_capacity?: number;
  wave_storage_capacity?: number;
  starting_wave_server_capacity?: number;
  wave_server_capacity_increase?: number;
  move_group_ids?: string[];
};

export interface WPMAllData {
  app?: DataLoadingState<Application>;
  database?: DataLoadingState<Database>;
  server?: DataLoadingState<Server>;
  move_group?: DataLoadingState<MoveGroup>;
  wave?: DataLoadingState<Wave>;
  wpm_job?: DataLoadingState<WPMJob>;
}
