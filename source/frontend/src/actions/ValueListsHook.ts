// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestStarted,
  requestSuccessful,
  reducer } from '../resources/reducer';

import { useReducer, useEffect, useState } from 'react';

import { Auth } from "@aws-amplify/auth";
import Tools from "../actions/tools";
import Login from "../actions/login";

export const useValueLists = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null
  });

  //Array of APIs that should be used to collect value lists for forms.
  const [valueListAPIs, setValueListAPIs] = useState([]);

  function addValueListItem (item){

    //Get current API list.
    let tmpvalueListAPIs = valueListAPIs;

    tmpvalueListAPIs.push(item);

    setValueListAPIs(tmpvalueListAPIs);

  }

  async function update() {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    let tempValueList = [];
    for ( const vlAPI of valueListAPIs) {
      let result = {
        values: [],
      }

      if (vlAPI === '/admin/groups'){
        try {

          const session = await Auth.currentSession();
          let apiLogin = await new Login(session);
          const response = await apiLogin.getGroups({ signal: myAbortController.signal });
          result = {
            values: response,
          }
          tempValueList[vlAPI] = result;

        } catch (e) {
          console.log(e);

          return () => {
            myAbortController.abort();
          };

        }
      } else {
        try {

          const session = await Auth.currentSession();
          let apiAutomation = await new Tools(session);
          const response = await apiAutomation.getTool(vlAPI, { signal: myAbortController.signal });
          result = {
            values: response,
          }
          tempValueList[vlAPI] = result;

        } catch (e) {
          if (e.message !== 'Request aborted') {
            console.error('Value Lists Hook', e);
          }

          return () => {
            myAbortController.abort();
          };

        }
      }
    }

    dispatch(requestSuccessful({data: tempValueList}));

    return () => {
      myAbortController.abort();
    };
  };

  useEffect(() => {
    let cancelledRequest;

    (async () => {
      await update();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };

  },[valueListAPIs]);

  return [state , { update, addValueListItem }];
};
