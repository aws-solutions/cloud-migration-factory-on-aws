// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestStarted,
  requestSuccessful,
  requestFailed,
  reducer, DataHook
} from '../resources/reducer';

import { useReducer, useEffect } from 'react';

import { Auth } from "@aws-amplify/auth";
import User from "../actions/user";

export const useGetServers: DataHook = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null
  });

  async function update(app_id) {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    try {

      const session = await Auth.currentSession();
      let apiUser = await new User(session);
      if (app_id) {
        let response = [];
        try {
          response = await apiUser.getAppServers(app_id, {signal: myAbortController.signal});
          dispatch(requestSuccessful({data: response}));
        } catch (e) {
          if ('response' in e && 'data' in e.response && 'errors' in e.response.data) {
            console.log(e.response.data.errors)
            dispatch(requestFailed({data: [], error: e.response.data.errors}));
            return;
          } else{
            console.log(e.response)
            dispatch(requestFailed({data: [], error: 'Error getting data from API.'}));
          }
        }
      } else {
        const response = await apiUser.getServers({ signal: myAbortController.signal });
        dispatch(requestSuccessful({data: response}));
      }
    } catch (e) {
      if (e.message !== 'Request aborted') {
        console.error('ServersHook', e);

      } else {

        console.error(e);
      }
      if (e.response && e.response.data){
        console.error(e.response.errors);
        dispatch(requestFailed({data: [], error: e.response.data}));
      } else {
        dispatch(requestFailed({data: [], error: 'unknown error'}));
      }
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

  },[]);

  return [state , { update }];
};
