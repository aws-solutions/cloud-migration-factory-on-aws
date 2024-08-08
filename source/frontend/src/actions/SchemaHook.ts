/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestFailed,
  requestRefresh,
  requestStarted,
  requestSuccessful,
  schemaReducer,
  SchemaReducerState,
} from "../resources/schemaReducer";

import { useEffect, useReducer } from "react";
import AdminApiClient from "../api_clients/adminApiClient";
import { EntitySchema, SchemaMetaData } from "../models/EntitySchema";

export const useSchema = (): [SchemaReducerState, { update: () => Promise<() => void> }] => {
  const initialState: {
    isLoading: boolean;
    schemas: Record<string, EntitySchema> | undefined;
    error: null;
    schemaMetadata: SchemaMetaData[] | undefined;
  } = {
    isLoading: true,
    schemas: undefined,
    schemaMetadata: undefined,
    error: null,
  };
  const [state, dispatch] = useReducer(schemaReducer, initialState);

  async function update() {
    const myAbortController = new AbortController();

    if (state.schemas) {
      console.log("schemas refresh started");
      dispatch(requestRefresh());
    } else {
      console.log("schemas load started");
      dispatch(requestStarted());
    }

    try {
      const apiAdmin = new AdminApiClient();

      const schemaMetadata = await apiAdmin.getSchemas();

      const schemas: Record<string, EntitySchema> = {};
      for (const schemaItem of schemaMetadata) {
        const entitySchema = await apiAdmin.getSchema(schemaItem.schema_name);

        // postprocess schema name to mitigate inconsistency between `app` and `application`
        if (schemaItem["schema_name"] === "app") {
          schemaItem["schema_name"] = "application";
        }

        schemas[schemaItem["schema_name"]] = entitySchema;
      }

      dispatch(requestSuccessful({ schemas, schemaMetadata }));
      console.log("schemas loaded");
    } catch (e: any) {
      if (e.message !== "Request aborted") {
        console.error("Schema Hook", e);
      }
      console.debug(e);
      let finalErrorText;
      const window1 = window as any;
      if (window1.env.API_VPCE_ID !== "") {
        finalErrorText =
          e +
          ", when trying to access API Gateway VPC Endpoint URL https://" +
          window1.env.API_ADMIN +
          "-" +
          window1.env.API_VPCE_ID +
          ".execute-api." +
          window1.env.API_REGION +
          ".amazonaws.com/prod. Please resolve the issue connecting from this device and retry.";
      } else {
        finalErrorText =
          e +
          ", when trying to access API Gateway URL " +
          "https://" +
          window1.env.API_ADMIN +
          ".execute-api." +
          window1.env.API_REGION +
          ".amazonaws.com/prod. Please resolve the issue connecting from this device and retry.";
      }
      dispatch(requestFailed({ error: finalErrorText }));
    }

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
  }, []);

  return [state, { update }];
};
