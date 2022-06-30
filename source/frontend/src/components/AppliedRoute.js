import React from "react";
import { Redirect, Route } from "react-router-dom";
import {
  StatusIndicator,
  Alert
 } from '@awsui/components-react';
import { useNavigate } from "react-router-dom";

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
