/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type Wave = {
  wave_id: string;
  wave_name: string;
  wave_description?: string;
  wave_status?: string;
  wave_start_time?: string;
  wave_end_time?: string;
  wave_servers_baseline?: string;
  wave_servers_forecast?: string;
  wave_apps_baseline?: string;
  wave_apps_forecast?: string;
  server_count: number;
  total_server_storage?: number;
  complexity_score?: number;
  wpm_job_id?: string;
  move_group_ids?: string[];
  app_ids?: string[];
  server_ids?: string[];
  database_ids?: string[];
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
