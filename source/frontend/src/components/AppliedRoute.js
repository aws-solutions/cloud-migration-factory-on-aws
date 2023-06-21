/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Route } from "react-router-dom";
import {
  StatusIndicator,
  Alert
 } from '@awsui/components-react';

export default ({ component: C, props: cProps, ...rest }) =>
  <Route
    {...rest}
    render={props =>
        cProps.isReady
        ?
        <C {...props} {...cProps} {...rest}/>
        :
        <center>
          {cProps.appError == null
            ?
            <StatusIndicator type="loading">
              Loading
            </StatusIndicator>
            :
            <Alert
              visible={true}
              type="error"
              header="Application Error"
            >
              {cProps.appError}
            </Alert>
          }
        </center>
    }
  /> ;
