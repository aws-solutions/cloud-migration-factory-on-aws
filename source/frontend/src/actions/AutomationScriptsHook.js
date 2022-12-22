/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestStarted,
  requestSuccessful,
  requestFailed,
  reducer } from '../resources/reducer.js';

import { useReducer, useEffect } from 'react';

import { Auth } from "aws-amplify";
import Tools from "../actions/tools";

export const useAutomationScripts = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null
  });

  function localDataRemoveItem(id) {
    return state.data.filter(function (entry) {
      return entry.filename !== id;
    });
  }

  async function deleteItems(deleteItems) {
    let apiTools = null;

    try {
      const session = await Auth.currentSession();
      apiTools = new Tools(session);
    } catch (e) {
      console.log(e);
    }

    for(let item in deleteItems) {
      try {
        //await apiTools.deleteApp(deleteItems[item].app_id);
        const lUpdatedData = localDataRemoveItem(deleteItems[item].app_id);
        dispatch(requestSuccessful({data: lUpdatedData}));
      } catch (err) {
        //Error deleting application.
      }

      // handleNotification({
      //       type: 'success',
      //       dismissible: true,
      //       header: 'Application deleted successfully',
      //       content: deleteItems[item].app_name + ' was deleted.'
      //     });

    }

    //If successful then no need to get all data again.
    //await update();


  }


  async function update() {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    try {

      const session = await Auth.currentSession();
      let apiAutomation = await new Tools(session);
      const response = await apiAutomation.getSSMScripts({ signal: myAbortController.signal });

      dispatch(requestSuccessful({data: response}));

    } catch (e) {
      if (e.message !== 'Request aborted') {
        console.error('Automation Scripts Hook', e);
      }
      dispatch(requestFailed({ error: e.message }));

      return () => {
        myAbortController.abort();
      };
    }

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

  },[]);

  return [state , { update }];
};
