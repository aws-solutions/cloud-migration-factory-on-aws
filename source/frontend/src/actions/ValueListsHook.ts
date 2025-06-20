/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { reducer, requestStarted, requestSuccessful } from "../resources/reducer";

import { useEffect, useReducer, useState } from "react";
import ToolsApiClient from "../api_clients/toolsApiClient";
import LoginApiClient from "../api_clients/loginApiClient";
import AdminApiClient from "../api_clients/adminApiClient";

export const useValueLists = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null,
  });

  //Array of APIs that should be used to collect value lists for forms.
  const [valueListAPIs, setValueListAPIs] = useState<any>([]);

  function addValueListItem(item: any) {
    //Get current API list.
    let tmpvalueListAPIs = valueListAPIs;

    tmpvalueListAPIs.push(item);

    setValueListAPIs(tmpvalueListAPIs);
  }

  async function update() {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    let tempValueList = [];
    for (const vlAPI of valueListAPIs) {
      let result = {
        values: [],
      };

      if (vlAPI === "/admin/groups") {
        try {
          let apiLogin = new LoginApiClient();
          const response = await apiLogin.getGroups();
          result = {
            values: response,
          };
          tempValueList[vlAPI] = result;
        } catch (e: any) {
          console.log(e);

          return () => {
            myAbortController.abort();
          };
        }
      } else if (vlAPI === "/admin/users") {
        try {
          let apiAdmin = new AdminApiClient();
          const response = await apiAdmin.getUsers();
          result = {
            values: response,
          };
          tempValueList[vlAPI] = result;
        } catch (e: any) {
          console.log(e);

          return () => {
            myAbortController.abort();
          };
        }
      } else {
        try {
          let apiAutomation = new ToolsApiClient();
          const response = await apiAutomation.getTool(vlAPI);
          result = {
            values: response,
          };
          tempValueList[vlAPI] = result;
        } catch (e: any) {
          if (e.message !== "Request aborted") {
            console.error("Value Lists Hook", e);
          }

          return () => {
            myAbortController.abort();
          };
        }
      }
    }

    dispatch(requestSuccessful({ data: tempValueList }));

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
  }, [valueListAPIs]);

  return [state, { update, addValueListItem }];
};
