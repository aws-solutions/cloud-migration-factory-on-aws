/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { reducer, requestStarted, requestSuccessful } from "../resources/reducer";

import { useCallback, useEffect, useReducer, useState } from "react";
import ToolsApiClient from "../api_clients/toolsApiClient";
import LoginApiClient from "../api_clients/loginApiClient";
import AdminApiClient from "../api_clients/adminApiClient";

const apiAutomation = new ToolsApiClient();
const apiLogin = new LoginApiClient();

export const useValueLists = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null,
  });

  //Array of APIs that should be used to collect value lists for forms.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [valueListAPIs, setValueListAPIs] = useState<any>([]);

  const addValueListItem = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (item: any) => {
      //Get current API list.
      const tmpvalueListAPIs = valueListAPIs;

      tmpvalueListAPIs.push(item);

      setValueListAPIs(tmpvalueListAPIs);
    },
    [valueListAPIs]
  );

  const update = useCallback(async () => {
    const myAbortController = new AbortController();

    dispatch(requestStarted());

    const tempValueList = [];
    for (const vlAPI of valueListAPIs) {
      let result = {
        values: [],
      };

      if (vlAPI === "/admin/groups") {
        try {
          const response = await apiLogin.getGroups();
          result = {
            values: response,
          };
          tempValueList[vlAPI] = result;
        } catch (e) {
          console.log(e);

          return () => {
            myAbortController.abort();
          };
        }
      } else if (vlAPI === "/admin/users") {
        try {
          const apiAdmin = new AdminApiClient();
          const response = await apiAdmin.getUsers();
          result = {
            values: response,
          };
          tempValueList[vlAPI] = result;
        } catch (e: unknown) {
          console.log(e);

          return () => {
            myAbortController.abort();
          };
        }
      } else {
        try {
          const response = await apiAutomation.getTool(vlAPI);
          result = {
            values: response,
          };
          tempValueList[vlAPI] = result;
        } catch (e) {
          if (e instanceof Error && e.message !== "Request aborted") {
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
  }, [valueListAPIs]);

  useEffect(() => {
    let cancelledRequest;

    (async () => {
      await update();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };
  }, [update, valueListAPIs]);

  return [state, { update, addValueListItem }];
};
