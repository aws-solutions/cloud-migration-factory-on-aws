import {
  requestStarted,
  requestSuccessful,
  requestFailed,
  reducer } from '../resources/permissionsReducer.js';

import { useReducer, useEffect } from 'react';

import { Auth } from "aws-amplify";
import Admin from "./admin";
import Login from "./login";

export const useAdminPermissions = () => {
  const emptyPermissions = {
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

    let permissions = {};

    let session = null;

    try {
      session = await Auth.currentSession();
    }
    catch(e) {
      if (session !== null) {
        console.error('Admin Permissions Hook', e);
        return;
      }
    }

    dispatch(requestStarted());

    try {
      let apiAdmin = await new Admin(session);

      permissions.roles = await apiAdmin.getRoles({ signal: myAbortController.signal });
      permissions.policies = await apiAdmin.getPolicies({ signal: myAbortController.signal });
      permissions.users = await apiAdmin.getUsers({ signal: myAbortController.signal });

    } catch (e) {
      if (e.message !== 'Request aborted') {
        console.error('Admin Permissions Hook', e);
      }
      dispatch(requestFailed({data: emptyPermissions, error: e}));

    }

    try{

      let apiLogin = await new Login(session);
      const response = await apiLogin.getGroups({ signal: myAbortController.signal });
      permissions.groups = response.map(group => {return {group_name: group}});

      dispatch(requestSuccessful({ data : permissions}));

    } catch (e) {
      if (e.message !== 'Request aborted') {
        console.error('Admin Permissions Hook', e);
      }
      dispatch(requestFailed({data: emptyPermissions, error: e}));
    }

    return () => {
      myAbortController.abort();
    };

  };

  useEffect(() => {
    let cancelledRequest;

    (async () => {
      await update();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };

  },[]);

  return [state , { update }];
};
