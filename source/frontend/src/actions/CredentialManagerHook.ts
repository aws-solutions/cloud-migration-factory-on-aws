/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { reducer, requestStarted, requestSuccessful } from "../resources/reducer";
import { Dispatch, useCallback, useEffect, useReducer } from "react";
import ToolsApiClient from "../api_clients/toolsApiClient";

const toolsAPI = new ToolsApiClient();

export const useCredentialManager = () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [state, dispatch]: [any, Dispatch<any>] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null,
  });

  const getSecretList = useCallback(async () => {
    const myAbortController = new AbortController();
    let credentialManagerData = [];

    dispatch(requestStarted());

    try {
      credentialManagerData = await toolsAPI.getCredentials();

      dispatch(requestSuccessful({ data: credentialManagerData }));
    } catch (e) {
      if (e instanceof Error && e.name !== "AbortError") {
        console.error("Credential Manager Hook", e);
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
      await getSecretList();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };
  }, [getSecretList]);

  return [state, { getSecretList }];
};
