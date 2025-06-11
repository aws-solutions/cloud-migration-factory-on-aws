/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type Database = {
  app_id: string;
  database_type: string;
  database_id: string;
  database_name: string;
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
