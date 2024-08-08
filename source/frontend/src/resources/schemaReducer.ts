/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { EntitySchema, SchemaMetaData } from "../models/EntitySchema";

enum RequestState {
  REQUEST_STARTED = "REQUEST_STARTED",
  REQUEST_SUCCESSFUL = "REQUEST_SUCCESSFUL",
  REQUEST_FAILED = "REQUEST_FAILED",
  RESET_REQUEST = "RESET_REQUEST",
  REQUEST_REFRESH = "REQUEST_REFRESH",
}

export type SchemaReducerState = {
  isLoading: boolean;
  schemas?: Record<string, EntitySchema>;
  schemaMetadata?: Array<SchemaMetaData>;
  error: any;
};

export type SchemaReducerAction = {
  type: RequestState;
  schemas?: Record<string, EntitySchema>;
  schemaMetadata?: Array<SchemaMetaData>;
  error?: any;
};

export const schemaReducer = (state: SchemaReducerState, action: SchemaReducerAction): SchemaReducerState => {
  // we check the type of each action and return an updated state object accordingly

  switch (action.type) {
    case RequestState.REQUEST_REFRESH:
      return {
        error: null,
        isLoading: false,
        schemas: state.schemas,
        schemaMetadata: state.schemaMetadata,
      };
    case RequestState.REQUEST_STARTED:
      return {
        error: null,
        isLoading: true,
        schemas: undefined,
        schemaMetadata: undefined,
      };
    case RequestState.REQUEST_SUCCESSFUL:
      return {
        isLoading: false,
        error: null,
        schemas: action.schemas,
        schemaMetadata: action.schemaMetadata,
      };
    case RequestState.REQUEST_FAILED:
      return {
        schemas: undefined,
        schemaMetadata: undefined,
        isLoading: false,
        error: action.error,
      };

    default:
      return {
        error: null,
        isLoading: true,
        schemas: state.schemas,
        schemaMetadata: state.schemaMetadata,
      };
  }
};

export const requestFailed = ({ error }: { error: any }) => ({
  type: RequestState.REQUEST_FAILED,
  error,
});

export const requestSuccessful = ({
  schemas,
  schemaMetadata,
}: {
  schemas: Record<string, EntitySchema>;
  schemaMetadata: Array<SchemaMetaData>;
}) => ({
  type: RequestState.REQUEST_SUCCESSFUL,
  schemas,
  schemaMetadata,
});

export const requestStarted = () => ({
  type: RequestState.REQUEST_STARTED,
});

export const requestRefresh = () => ({
  type: RequestState.REQUEST_REFRESH,
});
