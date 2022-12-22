/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestStarted,
  requestSuccessful,
  requestFailed,
  reducer } from '../resources/reducer.js';

import { useReducer, useEffect } from 'react';

import { Auth } from "aws-amplify";
import User from "../actions/user";

export const useMFWaves = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null
  });

  async function update() {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    try {

      const session = await Auth.currentSession();
      let apiUser = await new User(session);
      const response = await apiUser.getWaves({ signal: myAbortController.signal });

      dispatch(requestSuccessful({data: response}));

    } catch (e) {
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
