/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  PermissionsReducerState,
  reducer,
  requestFailed,
  requestStarted,
  requestSuccessful,
} from "../resources/permissionsReducer";

import { useCallback, useEffect, useReducer } from "react";
import AdminApiClient from "../api_clients/adminApiClient";
import LoginApiClient from "../api_clients/loginApiClient";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type PermissionsModel = { roles: any[]; policies: any[]; groups: any[]; users: any[] };

const apiAdmin = new AdminApiClient();
const apiLogin = new LoginApiClient();

const emptyPermissions: PermissionsModel = {
  policies: [],
  roles: [],
  groups: [],
  users: [],
};

export const useAdminPermissions: () => [PermissionsReducerState, { update: () => Promise<unknown> }] = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: emptyPermissions,
    error: null,
  });

  const update = useCallback(async () => {
    const myAbortController = new AbortController();
    const permissions = { ...emptyPermissions };

    dispatch(requestStarted());

    try {
      permissions.roles = await apiAdmin.getRoles();
      permissions.policies = await apiAdmin.getPolicies();
      permissions.users = await apiAdmin.getUsers();
    } catch (e) {
      if (e instanceof Error && e.message !== "Request aborted") {
        console.error("Admin Permissions Hook", e);
      }
      dispatch(requestFailed({ error: e }));
    }

    try {
      const response = await apiLogin.getGroups();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      permissions.groups = response.map((group: any) => {
        return { group_name: group };
      });

      dispatch(requestSuccessful({ data: permissions }));
    } catch (e) {
      if (e instanceof Error && e.message !== "Request aborted") {
        console.error("Admin Permissions Hook", e);
      }
      dispatch(requestFailed({ error: e }));
    }

    return () => {
      myAbortController.abort();
    };
  }, []);

  useEffect(() => {
    let cancelledRequest;

    (async () => {
      await update();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };
  }, [update]);

  return [state, { update }];
};
