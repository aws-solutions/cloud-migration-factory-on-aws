/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {DataHook, reducer, requestFailed, requestStarted, requestSuccessful} from '../resources/reducer';

import {useEffect, useReducer} from 'react';
import ToolsApiClient from "../api_clients/toolsApiClient";

export const useAutomationJobs: DataHook = () => {


  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null
  });

  async function update(maximumDays: number | undefined = undefined) {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    try {
      let apiAutomation = new ToolsApiClient();
      const response = await apiAutomation.getSSMJobs(maximumDays);

      dispatch(requestSuccessful({data: response}));

    } catch (e: any) {
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
  }

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
