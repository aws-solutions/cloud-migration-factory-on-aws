/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {DataHook, DataState, reducer, requestFailed, requestStarted, requestSuccessful} from '../resources/reducer';

import {useEffect, useReducer} from 'react';

import {Auth} from "@aws-amplify/auth";
import User from "../actions/user";

export const useMFWaves: DataHook = () => {
  const [state, dispatch]: [DataState, React.Dispatch<any>] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null
  });

  async function update(): Promise<() => void> {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    try {

      const session = await Auth.currentSession();
      let apiUser = new User(session);
      const response = await apiUser.getWaves();

      dispatch(requestSuccessful({data: response}));

    } catch (e: any) {
      if (e.message !== 'Request aborted') {
        console.error('Waves Hook', e);
      }
      dispatch(requestFailed({ error: e.message }));

      return () => {
        myAbortController.abort();
      };
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
