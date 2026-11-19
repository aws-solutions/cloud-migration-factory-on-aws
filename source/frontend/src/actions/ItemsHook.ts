/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { DataHook, reducer, requestFailed, requestStarted, requestSuccessful } from "../resources/reducer";

import { useCallback, useEffect, useReducer, useRef } from "react";
import UserApiClient from "../api_clients/userApiClient";

const userApiClient = new UserApiClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useGetItems: DataHook = <T = any>(schema: string) => {
  // The API clients do not support AbortController yet, use a ref to cancel inflight API calls on cleanup
  const cancelRef = useRef({ cancelled: false });

  const [state, dispatch] = useReducer(reducer<T>, {
    isLoading: true,
    data: [],
    error: null,
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const update_handle_exception = useCallback((e: any) => {
    if (e.message !== "Request aborted") {
      console.error("ItemsHook", e);
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

  /**
   * Updates the items from the API
   * @param schema - The schema to fetch items for
   */
  const update = useCallback(
    async (schema: string) => {
      const myAbortController = new AbortController();
      const localCancelRef = cancelRef.current;
      dispatch(requestStarted());

      try {
        const response = await userApiClient.getItems(schema);
        if (!localCancelRef.cancelled) {
          dispatch(requestSuccessful({ data: response }));
        }
      } catch (e) {
        if (!localCancelRef.cancelled) {
          update_handle_exception(e);
        }
      }

      return () => {
        myAbortController.abort();
      };
    },
    [update_handle_exception]
  );

  useEffect(() => {
    // Cancel the current and start a new one
    cancelRef.current.cancelled = true;
    const curCancelRef = { cancelled: false };
    cancelRef.current = curCancelRef;

    (async () => {
      await update(schema);
    })();

    return () => {
      curCancelRef.cancelled = true;
    };
  }, [schema, update]);

  return [state, { update }];
};
