/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { DataHook, reducer, requestFailed, requestStarted, requestSuccessful } from "../resources/reducer";

import { useEffect, useReducer } from "react";
import UserApiClient from "../api_clients/userApiClient";

export const useMFApps: DataHook = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null,
  });

  async function update() {
    const myAbortController = new AbortController();
    dispatch(requestStarted());

    try {
      const response = await new UserApiClient().getApps();

      dispatch(requestSuccessful({ data: response }));
    } catch (e: any) {
      if (e.message !== "Request aborted") {
        console.error("Applications Hook", e);
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
