/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type Wave = {
  wave_id: string;
  wave_name: string;
  wave_status?: string;
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
