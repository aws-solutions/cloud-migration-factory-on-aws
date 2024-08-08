/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { DataHook, DataState, reducer, requestFailed, requestStarted, requestSuccessful } from "../resources/reducer";

import { useEffect, useReducer } from "react";
import UserApiClient from "../api_clients/userApiClient";

export const useMFWaves: DataHook = () => {
  const [state, dispatch]: [DataState, React.Dispatch<any>] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null,
  });

  async function update(): Promise<() => void> {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    try {
      const response = await new UserApiClient().getWaves();

      dispatch(requestSuccessful({ data: response }));
    } catch (e: any) {
      if (e.message !== "Request aborted") {
        console.error("Waves Hook", e);
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
  }, []);

  return [state, { update }];
};
