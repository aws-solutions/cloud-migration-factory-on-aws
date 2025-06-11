/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type Application = {
  app_id: string;
  app_name: string;
  aws_region: string;
  wave_id: string;
  aws_accountid: string;
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
