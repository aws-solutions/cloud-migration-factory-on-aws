/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {reducer, requestStarted, requestSuccessful} from '../resources/reducer';
import {Dispatch, useEffect, useReducer} from 'react';
import ToolsApiClient from "../api_clients/toolsApiClient";

export const useCredentialManager = () => {

  const [state, dispatch]: [any, Dispatch<any>] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null
  });

  async function getSecretList() {
    const myAbortController = new AbortController();
    let credentialManagerData = [];

    dispatch(requestStarted());

    try {

      let toolsAPI = new ToolsApiClient();
      credentialManagerData = await toolsAPI.getCredentials();

      dispatch(requestSuccessful({ data: credentialManagerData }));

    } catch (e: any) {
      if (e.name !== 'AbortError') {
        console.error('Credential Manager Hook', e);
      }
      dispatch(requestSuccessful({ data: [] }));
    }

    return () => {
      myAbortController.abort();
    };

  }

  useEffect(() => {
    let cancelledRequest;

    (async () => {
      await getSecretList();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };

  }, []);

  return [state, { getSecretList }];
};
