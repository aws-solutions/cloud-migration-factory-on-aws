// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

const REQUEST_STARTED = 'REQUEST_STARTED';
const REQUEST_SUCCESSFUL = 'REQUEST_SUCCESSFUL';
const REQUEST_FAILED = 'REQUEST_FAILED';
const RESET_REQUEST = 'RESET_REQUEST';

export type DataState = {
  data?: any,
  error?: any,
  isLoading: boolean
}
export type DataHook = () => [DataState, UpdateFnWrapper];

export type UpdateFnWrapper = { update: () => Promise<() => void> };

export const reducer = (state: State, action) => {
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
  data?: any,
  error?: any
}

export const requestFailed = ({ data, error }: Payload) => ({
  type: REQUEST_FAILED,
  data,
  error,
});

export const requestSuccessful = ({ data }) => ({
  type: REQUEST_SUCCESSFUL,
  data,
});

export const requestStarted = () => ({
  type: REQUEST_STARTED
});
