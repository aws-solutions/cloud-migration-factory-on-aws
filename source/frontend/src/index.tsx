// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { createRoot } from 'react-dom/client';
import { Amplify } from '@aws-amplify/core'
import App from './App';
import "@awsui/global-styles/index.css"
import { BrowserRouter } from 'react-router-dom';

let awsConfig = {
  Auth: {
    mandatorySignIn: true,
    region: window.env.COGNITO_REGION,
    userPoolId: window.env.COGNITO_USER_POOL_ID,
    userPoolWebClientId: window.env.COGNITO_APP_CLIENT_ID,
  },
  API: {
    endpoints: []
  }
};

let vpce_id = '';
if (window.env.API_VPCE_ID !== ''){
  vpce_id = "-" + window.env.API_VPCE_ID
}

awsConfig.API.endpoints = [
    {
      name: "admin",
      endpoint: 'https://' + window.env.API_ADMIN + vpce_id + '.execute-api.' + window.env.API_REGION + '.amazonaws.com/prod',
      region: window.env.API_REGION
    },
    {
      name: "user",
      endpoint: 'https://' + window.env.API_USER + vpce_id + '.execute-api.' + window.env.API_REGION + '.amazonaws.com/prod',
      region: window.env.API_REGION
    },
    {
      name: "login",
      endpoint: 'https://' + window.env.API_LOGIN + vpce_id + '.execute-api.' + window.env.API_REGION + '.amazonaws.com/prod',
      region: window.env.API_REGION
    },
    {
      name: "tools",
      endpoint: 'https://' + window.env.API_TOOLS + vpce_id + '.execute-api.' + window.env.API_REGION + '.amazonaws.com/prod',
      region: window.env.API_REGION
    }
  ]

const oauthSettings = {
  domain: window.env.COGNITO_HOSTED_UI_URL,
    scope: ['phone', 'email', 'openid', 'aws.cognito.signin.user.admin'],
    redirectSignIn: window.location.origin + '/',
    redirectSignOut: window.location.origin + '/',
    responseType: 'code' // or 'token', note that REFRESH token will only be generated when the responseType is code
}

const updatedAwsConfig = {
  ...awsConfig,
  Auth: {
    ...awsConfig.Auth,
    oauth: {
      ...oauthSettings
    }
  }
}

Amplify.configure(updatedAwsConfig);

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById("root");
  const root = createRoot(container);
  root.render(
      <BrowserRouter>
      <App />
    </BrowserRouter>
  );
});
