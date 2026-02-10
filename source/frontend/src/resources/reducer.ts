/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { DataLoadingState } from "../models/EntitySchema";

const REQUEST_STARTED = "REQUEST_STARTED";
const REQUEST_SUCCESSFUL = "REQUEST_SUCCESSFUL";
const REQUEST_FAILED = "REQUEST_FAILED";

export type DataHook = <T = any>(arg0?: any) => [DataLoadingState<T>, UpdateFnWrapper];

export type UpdateFnWrapper = { update: (arg0?: any) => Promise<() => void> };

export const reducer = <T = any>(
  state: DataLoadingState<T>,
  action: {
    type: string;
    data: T[];
    error?: any;
  }
): DataLoadingState<T> => {
  // we check the type of each action and return an updated state object accordingly
  switch (action.type) {
    case REQUEST_SUCCESSFUL:
      return {
        isLoading: false,
        error: null,
        data: action.data,
      };
    case REQUEST_FAILED:
      return {
        data: [],
        isLoading: false,
        error: action.error,
      };
    default:
      return {
        error: null,
        isLoading: true,
        data: [],
      };
  }
};

export type Payload = {
  data?: any;
  error?: any;
};

export const requestFailed = ({ data, error }: Payload) => ({
  type: REQUEST_FAILED,
  data,
  error,
});

export const requestSuccessful = ({ data }: Payload) => ({
  type: REQUEST_SUCCESSFUL,
  data,
});

export const requestStarted = () => ({
  type: REQUEST_STARTED,
  data: [],
});
