/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import UserApiClient from "../api_clients/userApiClient";
import { CustomAsset, DataLoadingState, EntitySchema } from "../models";
import { UNEXPECTED_ERROR } from "../resources/recordFunctions";

const userApiClient = new UserApiClient();

type CancelRef = {
  cancelled: boolean;
};

type CustomAssetItemsHook = [Record<string, DataLoadingState<CustomAsset>>, () => void];

/**
 * React hook that manages loading states for custom asset items from multiple schemas.
 * Automatically fetches custom assets when entity schemas change and provides a reload function.
 *
 * @param schemas - Record of entity schemas keyed by entity name
 * @returns A tuple containing:
 *   - loadingStates: Record mapping schema names to their loading states (data, loading, error)
 *   - reload: Function to manually reload all custom asset items
 */
export const useCustomAssetItems = (schemas: Readonly<Record<string, EntitySchema>>): CustomAssetItemsHook => {
  const [loadingStates, setLoadingStates] = React.useState<Record<string, DataLoadingState<CustomAsset>>>({});

  // The API clients do not support AbortController yet, use a ref to cancel inflight API calls on cleanup
  const cancelRef = React.useRef<CancelRef>({ cancelled: false });

  const customAssetSchemas = React.useMemo(
    () => Object.values(schemas).filter((schema) => schema.schema_type === "custom"),
    [schemas]
  );

  const fetchItems = async (schema: string) => {
    const localCancelRef = cancelRef.current;
    setLoadingStates((prev) => ({
      ...prev,
      [schema]: {
        ...prev[schema],
        isLoading: true,
        data: [],
        error: undefined,
      },
    }));

    try {
      const items = await userApiClient.getItems(schema);

      if (!localCancelRef.cancelled) {
        setLoadingStates((prev) => ({
          ...prev,
          [schema]: {
            data: items,
            isLoading: false,
            error: undefined,
          },
        }));
      }
    } catch (error) {
      if (!localCancelRef.cancelled) {
        setLoadingStates((prev) => ({
          ...prev,
          [schema]: {
            data: [],
            isLoading: false,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            error: (error as Error).message ?? (error as any).response?.data ?? UNEXPECTED_ERROR,
          },
        }));
      }
    }
  };

  // Fetch all items when schemaNames changes
  React.useEffect(() => {
    // Cancel the current and start a new one
    cancelRef.current.cancelled = true;
    const curCancelRef = { cancelled: false };
    cancelRef.current = curCancelRef;

    customAssetSchemas.forEach((md) => fetchItems(md.schema_name));

    return () => {
      curCancelRef.cancelled = true;
    };
  }, [customAssetSchemas]);

  // Function to reload items for all schemas
  const reload = React.useCallback(() => {
    cancelRef.current.cancelled = true;
    cancelRef.current = { cancelled: false };

    customAssetSchemas.forEach((md) => fetchItems(md.schema_name));
  }, [customAssetSchemas]);

  return [loadingStates, reload];
};
