/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  requestStarted,
  requestSuccessful,
  requestFailed,
  reducer, requestRefresh
} from '../resources/schemaReducer.js';

import { useReducer, useEffect } from 'react';

import { Auth } from "aws-amplify";
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
    var schema = {};
    var schemaMetadata = [];

    if (state.schema !== null && state.schemaMetadata !== null ){
      console.log('schema refresh started');
      dispatch(requestRefresh());
    } else {
      console.log('schema load started');
      dispatch(requestStarted());
    }

    try {

      const session = await Auth.currentSession();
      let apiAdmin = await new Admin(session  );

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
      dispatch(requestFailed({error: e}));
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
