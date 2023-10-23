// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestStarted,
  requestSuccessful,
  requestFailed,
  reducer, requestRefresh
} from '../resources/schemaReducer';

import { useReducer, useEffect } from 'react';

import { Auth } from "@aws-amplify/auth";
import Admin from "../actions/admin";

export const useSchema = () => {
  const emptySchema = {
    application: [],
    server: [],
    database: [],
    wave: [],
    secret: [],
    script: [],
    role: [],
    policy: [],
    automation: []
  }

  const [state, dispatch] = useReducer(reducer, {
    isLoading: true,
    data: emptySchema,
    schemaMetadata: [],
    error: null
  });

  async function update() {
    const myAbortController = new AbortController();
    let schema = {};
    let schemaMetadata = [];

    if (state.schema !== null && state.schemaMetadata !== null ){
      console.log('schema refresh started');
      dispatch(requestRefresh());
    } else {
      console.log('schema load started');
      dispatch(requestStarted());
    }

    try {
      let apiAdmin = await Admin.initializeCurrentSession();

      schemaMetadata = await apiAdmin.getSchemas();

      for (const schemaItem of schemaMetadata) {
        let schemaResp = await apiAdmin.getSchema(schemaItem.schema_name)
        if (schemaItem['schema_name'] === 'app') {
          schemaItem['schema_name'] = 'application';
          schema['application'] = schemaResp;
        } else {
          schema[schemaItem['schema_name']] = schemaResp;
        }
      }

      dispatch(requestSuccessful({'schema': schema, 'schemaMetadata': schemaMetadata}));
      console.log('schema loaded');

    } catch (e) {
      if (e.message !== 'Request aborted') {
        console.error('Schema Hook', e);
      }
      console.debug(e);
      let finalErrorText = ''
      if (window.env.API_VPCE_ID !== ''){
        finalErrorText = e + ', when trying to access API Gateway VPC Endpoint URL https://' +
           window.env.API_ADMIN + '-' + window.env.API_VPCE_ID + '.execute-api.' + window.env.API_REGION + '.amazonaws.com/prod. Please resolve the issue connecting from this device and retry.'
      } else {
        finalErrorText = e   + ', when trying to access API Gateway URL ' +
          'https://' + window.env.API_ADMIN + '.execute-api.' + window.env.API_REGION + '.amazonaws.com/prod. Please resolve the issue connecting from this device and retry.'
      }
      dispatch(requestFailed({error: finalErrorText}));
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

  },[]);

  return [state , { update }];
};
