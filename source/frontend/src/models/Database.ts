/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type Database = {
  // System fields
  database_id: string;
  database_name: string;
  database_type: string;
  // Application related fields
  app_ids?: string[];
  // Migration field
  r_type?: string;

  // WPM fields
  move_group_id?: string;
  wpm_job_id?: string;
  wave_id?: string;

  // Audit
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
