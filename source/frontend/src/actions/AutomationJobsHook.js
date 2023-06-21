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

import { Auth } from "@aws-amplify/auth";
import Tools from "../actions/tools";

export const useAutomationJobs = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null
  });

  async function update(maximumDays = undefined) {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    try {

      const session = await Auth.currentSession();
      let apiAutomation = await new Tools(session);
      const response = await apiAutomation.getSSMJobs(maximumDays ,{ signal: myAbortController.signal });

      dispatch(requestSuccessful({data: response}));

    } catch (e) {
      if (e.message !== 'Request aborted') {
        console.error('Automation Jobs Hook', e);
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
      await update(30);
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };

  },[]);

  return [state , { update }];
};
