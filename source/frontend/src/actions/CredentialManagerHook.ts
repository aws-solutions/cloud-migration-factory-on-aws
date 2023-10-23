// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestStarted,
  requestSuccessful,
  reducer
} from '../resources/reducer';
import { useReducer, useEffect } from 'react';
import Tools from "./tools";

export const useCredentialManager = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [] ,
    error: null
  });

  async function getSecretList() {
    const myAbortController = new AbortController();
    let credentialManagerData = [];

    dispatch(requestStarted());

    try {

      let toolsAPI = await Tools.initializeCurrentSession();
      credentialManagerData = await toolsAPI.getCredentials({ signal: myAbortController.signal })

      dispatch(requestSuccessful({ data: credentialManagerData }));

    } catch (e) {
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
