/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { useCallback, useEffect, useState } from "react";
import ToolsApiClient from "../api_clients/toolsApiClient";
import { DataUploadJob } from "../models";

const apiTools = new ToolsApiClient();

export type SingleDataLoadingState<T> = {
  data: T | undefined;
  isLoading: boolean;
  error?: string | null;
};

/**
 * Hook for fetching a specific data upload job by ID
 * @param jobId - The ID of the job to fetch
 * @returns State object with loading status, data, and error information
 */
export const useGetDataUploadJob = (
  jobId: string
): [SingleDataLoadingState<DataUploadJob>, { update: () => Promise<void> }] => {
  const [state, setState] = useState<SingleDataLoadingState<DataUploadJob>>({
    isLoading: true,
    data: undefined,
    error: null,
  });

  const update = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await apiTools.getUploadDataJob(jobId);
      setState({
        isLoading: false,
        data: response,
        error: null,
      });
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Unknown error occurred";
      console.error("DataUploadJob Hook", e);
      setState({
        isLoading: false,
        data: undefined,
        error: errorMessage,
      });
    }
  }, [jobId]);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      if (!cancelled) {
        await update();
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [update]);

  return [state, { update }];
};
