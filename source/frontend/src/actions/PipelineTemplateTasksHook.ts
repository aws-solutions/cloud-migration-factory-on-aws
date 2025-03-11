/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { DataHook, reducer, requestStarted, requestSuccessful } from "../resources/reducer";

import { useEffect, useReducer } from "react";
import UserApiClient from "../api_clients/userApiClient";

export const useGetPipelineTemplateTasks: DataHook = () => {
  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: [],
    error: null,
  });

  const apiUser = new UserApiClient();

  async function init() {
    const myAbortController = new AbortController();
    dispatch(requestStarted());

    try {
      const response = await apiUser.getPipelineTemplateTasks();
      dispatch(requestSuccessful({ data: response }));
    } catch (e: any) {
      if (e.message !== "Request aborted") {
        console.error("PipelineTemplateTasks Hook", e);
      }
      dispatch(requestSuccessful({ data: [] }));
    }

    return () => {
      myAbortController.abort();
    };
  }

  async function update() {
    const myAbortController = new AbortController();

    try {
      const response = await apiUser.getPipelineTemplateTasks();
      dispatch(requestSuccessful({ data: response }));
    } catch (e: any) {
      if (e.message !== "Request aborted") {
        console.error("PipelineTemplateTasks Hook", e);
      }
    }

    return () => {
      myAbortController.abort();
    };
  }

  useEffect(() => {
    let cancelledRequest;

    (async () => {
      await init();
      if (cancelledRequest) return;
    })();

    return () => {
      cancelledRequest = true;
    };
  }, []);

  return [state, { update }];
};
