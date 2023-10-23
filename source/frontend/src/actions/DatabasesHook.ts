// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestStarted,
  requestSuccessful,
  reducer, DataHook
} from '../resources/reducer';

import { useReducer, useEffect } from 'react';

import { Auth } from "@aws-amplify/auth";
import User from "../actions/user";

export const useGetDatabases: DataHook = () => {
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
          response = await apiUser.getAppDatabases(app_id, {signal: myAbortController.signal});
        } catch (e) {
          if ('response' in e && 'data' in e.response) {
            if (e.response.data.toLowerCase().indexOf('does not exist')){
              console.log('App Id ' + app_id + ' either does not exist or has no databases related.')
            } else {
              console.log(e.response.data)
            }
          } else{
            console.log('Unknown error occurred')
          }
        }
        dispatch(requestSuccessful({data: response}));
      } else {
        const response = await apiUser.getDatabases({ signal: myAbortController.signal });
        dispatch(requestSuccessful({data: response}));
      }
    } catch (e) {
      if (e.message !== 'Request aborted') {
        console.error('Databases Hook', e);
      }
      dispatch(requestSuccessful({data: []}));
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
