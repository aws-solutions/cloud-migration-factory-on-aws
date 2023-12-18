/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

const REQUEST_STARTED = 'REQUEST_STARTED';
const REQUEST_SUCCESSFUL = 'REQUEST_SUCCESSFUL';
const REQUEST_FAILED = 'REQUEST_FAILED';
const RESET_REQUEST = 'RESET_REQUEST';

export type AdminPermissions = { roles: any[]; policies: any[]; groups: any[]; users: any[] };
export type PermissionsReducerState = {
  isLoading: boolean; data: AdminPermissions; error: any
};
export const reducer: (state: any, action: any) => PermissionsReducerState = (state, action) => {
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
        data: {"policies": [], "roles": [], "groups": [], users: []} as AdminPermissions,
        isLoading: false,
        error: action.error,
      };
    default:
      return {
        error: null,
        isLoading: true,
        data: {"policies": [], "roles": [], "groups": [], users: []} as AdminPermissions,
      };
  }
};


export const requestFailed = ({error}: { error: any }) => ({
  type: REQUEST_FAILED,
  error,
});

export const requestSuccessful = ({data}: { data: AdminPermissions }) => ({
  type: REQUEST_SUCCESSFUL,
  data,
});

export const requestStarted = () => ({
  type: REQUEST_STARTED
});
