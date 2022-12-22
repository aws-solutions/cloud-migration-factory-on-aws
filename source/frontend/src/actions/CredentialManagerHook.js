/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestStarted,
  requestSuccessful,
  reducer
} from '../resources/reducer';
import { Auth } from "aws-amplify";
import { useReducer, useEffect } from 'react';

export const useCredentialManager = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [] ,
    error: null
  });

  async function getSecretList() {
    const myAbortController = new AbortController();
    var credentialManagerData = [];

    dispatch(requestStarted());

    try {
      const session = await Auth.currentSession();
      const token = session.idToken.jwtToken;

      const options = {
        headers: {
          Authorization: token
        },
        signal: myAbortController.signal
      };

      var response = await fetch(window.env.API_TOOLS + "/credentialmanager", options);
      credentialManagerData = await response.json();

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
