/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { DataHook, reducer, requestFailed, requestStarted, requestSuccessful } from "../resources/reducer";

import { useCallback, useEffect, useReducer } from "react";
import UserApiClient from "../api_clients/userApiClient";

const user = new UserApiClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useGetServers: DataHook = <T = any>() => {
  const [state, dispatch] = useReducer(reducer<T>, {
    isLoading: true,
    data: [],
    error: null,
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const update_handle_exception = useCallback((e: any) => {
    if (e.message !== "Request aborted") {
      console.error("ServersHook", e);
    } else {
      console.error(e);
    }
    if (e.response?.data) {
      console.error(e.response.errors);
      dispatch(requestFailed({ data: [], error: e.response.data }));
    } else {
      dispatch(requestFailed({ data: [], error: "unknown error" }));
    }
  }, []);

  const update = useCallback(async () => {
    const myAbortController = new AbortController();
    dispatch(requestStarted());

    try {
      const response = await user.getServers();
      dispatch(requestSuccessful({ data: response }));
    } catch (e) {
      update_handle_exception(e);
    }

    return () => {
      myAbortController.abort();
    };
  }, [update_handle_exception]);

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
