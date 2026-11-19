/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type Application = {
  app_id: string;
  app_name: string;
  aws_region?: string;
  aws_accountid?: string;
  move_group_ids?: string[];
  database_ids?: string[];
  server_ids?: string[];
  wpm_job_ids?: string[];
  wave_ids?: string[];
  // For dynamic properties ending with _ids
  [key: `${string}_ids`]: string[] | undefined;
  planning_status?: "NOT_STARTED" | "PARTIAL" | "COMPLETED";
  rank?: string; // even decimal fields are returned as strings
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};

/**
 * Extended Application type for use in Wave Planning Management components only.
 * Contains frontend-only properties that should not be sent to the backend.
 */
export type WPMApplication = Application & {
  /**
   * Frontend-only field used for temporary assignment to a WPM job.
   * This field should never be sent to the backend.
   */
  curr_wpm_job_id?: string;
};
