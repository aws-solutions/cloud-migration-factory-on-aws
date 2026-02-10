/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { DataHook, reducer, requestStarted, requestSuccessful } from "../resources/reducer";

import { useCallback, useEffect, useReducer } from "react";
import UserApiClient from "../api_clients/userApiClient";

const apiUser = new UserApiClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useGetDatabases: DataHook = <T = any>() => {
  const [state, dispatch] = useReducer(reducer<T>, {
    isLoading: true,
    data: [],
    error: null,
  });

  const update = useCallback(async () => {
    const myAbortController = new AbortController();
    dispatch(requestStarted());

    try {
      const response = await apiUser.getDatabases();
      dispatch(requestSuccessful({ data: response }));
    } catch (e) {
      if (e instanceof Error && e.message !== "Request aborted") {
        console.error("Databases Hook", e);
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
      await update();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };
  }, [update]);

  return [state, { update }];
};
