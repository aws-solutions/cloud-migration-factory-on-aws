/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  PermissionsReducerState,
  reducer,
  requestFailed,
  requestStarted,
  requestSuccessful
} from '../resources/permissionsReducer';

import {useEffect, useReducer} from 'react';
import AdminApiClient from "../api_clients/adminApiClient";
import LoginApiClient from "../api_clients/loginApiClient";

export type PermissionsModel = { roles: any[]; policies: any[]; groups: any[]; users: any[] };

export const useAdminPermissions: () => [PermissionsReducerState, { update: () => Promise<unknown> }] = () => {

  const emptyPermissions: PermissionsModel = {
    policies: [],
    roles: [],
    groups: [],
    users: []
  }

  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: emptyPermissions,
    error: null
  });

  async function update() {
    const myAbortController = new AbortController();
    const permissions = {...emptyPermissions};

    dispatch(requestStarted());

    try {
      let apiAdmin = new AdminApiClient();

      permissions.roles = await apiAdmin.getRoles();
      permissions.policies = await apiAdmin.getPolicies();
      permissions.users = await apiAdmin.getUsers();

    } catch (e: any) {
      if (e.message !== 'Request aborted') {
        console.error('Admin Permissions Hook', e);
      }
      dispatch(requestFailed({error: e}));
    }

    try {
      let apiLogin = new LoginApiClient();
      const response = await apiLogin.getGroups();
      permissions.groups = response.map((group: any) => {
        return {group_name: group}
      });

      dispatch(requestSuccessful({data: permissions}));

    } catch (e: any) {
      if (e.message !== 'Request aborted') {
        console.error('Admin Permissions Hook', e);
      }
      dispatch(requestFailed({error: e}));
    }

    return () => {
      myAbortController.abort();
    };

  }

  useEffect(() => {
    let cancelledRequest;

    (async () => {
      await update();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };

  }, []);

  return [state, {update}];
};
