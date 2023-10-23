// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

const REQUEST_STARTED = 'REQUEST_STARTED';
const REQUEST_SUCCESSFUL = 'REQUEST_SUCCESSFUL';
const REQUEST_FAILED = 'REQUEST_FAILED';
const RESET_REQUEST = 'RESET_REQUEST';
const REQUEST_REFRESH = 'REQUEST_REFRESH';

export const reducer = (state, action) => {
  // we check the type of each action and return an updated state object accordingly

  switch (action.type) {
    case REQUEST_REFRESH:
      return {
        error: null,
        isLoading: false,
        schema: state.schema,
        schemaMetadata: state.schemaMetadata
      };
    case REQUEST_STARTED:
      return {
        error: null,
        isLoading: true,
        schema: undefined,
        schemaMetadata: undefined
      };
    case REQUEST_SUCCESSFUL:
      return {
        isLoading: false,
        error: null,
        schema: action.schema,
        schemaMetadata: action.schemaMetadata
      };
    case REQUEST_FAILED:
      return {
        schema: null,
        schemaMetadata: null,
        isLoading: false,
        error: action.error,
      };

    default:
      return {
        error: null,
        isLoading: true,
        schema: state.schema,
        schemaMetadata: state.schemaMetadata
      };
  }
};


export const requestFailed = ({ error }) => ({
  type: REQUEST_FAILED,
  error,
});

export const requestSuccessful = ({ schema, schemaMetadata }) => (
  {
  type: REQUEST_SUCCESSFUL,
  schema,
  schemaMetadata
});

export const requestStarted = () => ({
  type: REQUEST_STARTED
});

export const requestRefresh = () => ({
  type: REQUEST_REFRESH
});
