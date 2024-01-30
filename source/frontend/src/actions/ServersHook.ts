/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {DataHook, reducer, requestFailed, requestStarted, requestSuccessful} from '../resources/reducer';

import {useEffect, useReducer} from 'react';
import UserApiClient from "../api_clients/userApiClient";

export const useGetServers: DataHook = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null,
  });


  async function update(app_id?: string) {
    const myAbortController = new AbortController();
    dispatch(requestStarted());

    try {
      const user = new UserApiClient();
      if (app_id) {
        let response = [];
        try {
          response = await user.getAppServers(app_id);
          dispatch(requestSuccessful({data: response}));
        } catch (e: any) {
          if (e.response?.data?.errors) {
            console.log(e.response.data.errors)
            dispatch(requestFailed({data: [], error: e.response.data.errors}));
            return () => {
              myAbortController.abort();
            };
          } else {
            console.log(e.response)
            dispatch(requestFailed({data: [], error: 'Error getting data from API.'}));
          }
        }
      } else {
        const response = await user.getServers();
        dispatch(requestSuccessful({data: response}));
      }
    } catch (e: any) {
      update_handle_exception(e);
    }

    return () => {
      myAbortController.abort();
    };
  }

  function update_handle_exception(e: any) {
    if (e.message !== 'Request aborted') {
      console.error('ServersHook', e);
    } else {
      console.error(e);
    }
    if (e.response?.data) {
      console.error(e.response.errors);
      dispatch(requestFailed({data: [], error: e.response.data}));
    } else {
      dispatch(requestFailed({data: [], error: 'unknown error'}));
    }
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
