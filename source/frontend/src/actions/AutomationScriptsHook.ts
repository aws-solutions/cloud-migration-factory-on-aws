/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { DataHook, reducer, requestFailed, requestStarted, requestSuccessful } from "../resources/reducer";

import { useCallback, useEffect, useReducer } from "react";
import ToolsApiClient from "../api_clients/toolsApiClient";

const apiAutomation = new ToolsApiClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useAutomationScripts: DataHook = <T = any>() => {
  const [state, dispatch] = useReducer(reducer<T>, {
    isLoading: true,
    data: [],
    error: null,
  });

  const update = useCallback(async () => {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    try {
      const response = await apiAutomation.getSSMScripts();

      dispatch(requestSuccessful({ data: response }));
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (e: any) {
      if (e.message !== "Request aborted") {
        console.error("Automation Scripts Hook", e);
      }
      dispatch(requestFailed({ error: e.message }));

      return () => {
        myAbortController.abort();
      };
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
