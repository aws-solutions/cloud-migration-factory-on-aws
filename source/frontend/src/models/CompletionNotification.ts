/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type CompletionNotification = {
  id?: string;
  increment: number;
  percentageComplete: number;
  status: string;
  importName?: any;
};
