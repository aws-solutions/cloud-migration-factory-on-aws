/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { DataHook, reducer, requestStarted, requestSuccessful } from "../resources/reducer";

import { useCallback, useEffect, useReducer } from "react";
import UserApiClient from "../api_clients/userApiClient";

const apiUser = new UserApiClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useGetTaskExecutions: DataHook = <T = any>() => {
  const [state, dispatch] = useReducer(reducer<T>, {
    isLoading: true,
    data: [],
    error: null,
  });

  const update = useCallback(async () => {
    const myAbortController = new AbortController();

    try {
      const response = await apiUser.getTaskExecutions();
      dispatch(requestSuccessful({ data: response }));
    } catch (e) {
      if (e instanceof Error && e.message !== "Request aborted") {
        console.error("TaskExecutions Hook", e);
      }
    }

    return () => {
      myAbortController.abort();
    };
  }, []);

  const init = useCallback(async () => {
    const myAbortController = new AbortController();
    dispatch(requestStarted());

    try {
      const response = await apiUser.getTaskExecutions();
      dispatch(requestSuccessful({ data: response }));
    } catch (e) {
      if (e instanceof Error && e.message !== "Request aborted") {
        console.error("TaskExecutions Hook", e);
      }
      dispatch(requestSuccessful({ data: [] }));
    }

    return () => {
      myAbortController.abort();
    };
  }, []);

  useEffect(() => {
    let cancelledRequest;

    (async () => {
      await init();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };
  }, [init]);

  return [state, { update }];
};
