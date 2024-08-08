/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { createRoot } from "react-dom/client";
import { Amplify } from "@aws-amplify/core";
import App from "./App";
import "@awsui/global-styles/index.css";
import { BrowserRouter } from "react-router-dom";
import { SessionContextProvider } from "./contexts/SessionContext";
import { Auth } from "@aws-amplify/auth";
import { NotificationContextProvider } from "./contexts/NotificationContext";
import { ToolsContextProvider } from "./contexts/ToolsContext";

const env = (window as any).env;

type EndpointConfig = {
  name: string;
  endpoint: string;
  region: string;
  custom_header: () => {};
};
let awsConfig: {
  Auth: { userPoolWebClientId: string; region: string; userPoolId: string; mandatorySignIn: boolean };
  API: { endpoints: EndpointConfig[] };
} = {
  Auth: {
    mandatorySignIn: true,
    region: env.COGNITO_REGION,
    userPoolId: env.COGNITO_USER_POOL_ID,
    userPoolWebClientId: env.COGNITO_APP_CLIENT_ID,
  },
  API: {
    endpoints: [],
  },
};

if (!env.API_VPCE_ID) {
  // by adding the custom header builder to each API endpoint below,
  // we avoid having to set the authentication headers within our application code
  const customHeaderBuilder = async () => {
    const session = await Auth.currentSession();
    return {
      Authorization: session.getIdToken().getJwtToken(),
      "Authorization-Access": session.getAccessToken().getJwtToken(),
    };
  };

  awsConfig.API.endpoints = [
    {
      name: "admin",
      endpoint: "https://" + env.API_ADMIN + ".execute-api." + env.API_REGION + ".amazonaws.com/prod",
      region: env.API_REGION,
      custom_header: customHeaderBuilder,
    },
    {
      name: "user",
      endpoint: "https://" + env.API_USER + ".execute-api." + env.API_REGION + ".amazonaws.com/prod",
      region: env.API_REGION,
      custom_header: customHeaderBuilder,
    },
    {
      name: "login",
      endpoint: "https://" + env.API_LOGIN + ".execute-api." + env.API_REGION + ".amazonaws.com/prod",
      region: env.API_REGION,
      custom_header: customHeaderBuilder,
    },
    {
      name: "tools",
      endpoint: "https://" + env.API_TOOLS + ".execute-api." + env.API_REGION + ".amazonaws.com/prod",
      region: env.API_REGION,
      custom_header: customHeaderBuilder,
    },
  ];
} else {
  // If deployment is using an API Gateway VPCE then API URL to VPCE and pass API ID as request header.

  awsConfig.API.endpoints = [
    {
      name: "admin",
      endpoint:
        "https://" + env.API_ADMIN + "-" + env.API_VPCE_ID + ".execute-api." + env.API_REGION + ".amazonaws.com/prod",
      region: env.API_REGION,
      custom_header: async () => {
        const session = await Auth.currentSession();
        return {
          Authorization: session.getIdToken().getJwtToken(),
          "Authorization-Access": session.getAccessToken().getJwtToken(),
        };
      },
    },
    {
      name: "user",
      endpoint:
        "https://" + env.API_USER + "-" + env.API_VPCE_ID + ".execute-api." + env.API_REGION + ".amazonaws.com/prod",
      region: env.API_REGION,
      custom_header: async () => {
        const session = await Auth.currentSession();
        return {
          Authorization: session.getIdToken().getJwtToken(),
          "Authorization-Access": session.getAccessToken().getJwtToken(),
        };
      },
    },
    {
      name: "login",
      endpoint:
        "https://" + env.API_LOGIN + "-" + env.API_VPCE_ID + ".execute-api." + env.API_REGION + ".amazonaws.com/prod",
      region: env.API_REGION,
      custom_header: async () => {
        const session = await Auth.currentSession();
        return {
          Authorization: session.getIdToken().getJwtToken(),
          "Authorization-Access": session.getAccessToken().getJwtToken(),
        };
      },
    },
    {
      name: "tools",
      endpoint:
        "https://" + env.API_TOOLS + "-" + env.API_VPCE_ID + ".execute-api." + env.API_REGION + ".amazonaws.com/prod",
      region: env.API_REGION,
      custom_header: async () => {
        const session = await Auth.currentSession();
        return {
          Authorization: session.getIdToken().getJwtToken(),
          "Authorization-Access": session.getAccessToken().getJwtToken(),
        };
      },
    },
  ];
}

const oauthSettings = {
  domain: env.COGNITO_HOSTED_UI_URL,
  scope: ["phone", "email", "openid", "aws.cognito.signin.user.admin"],
  redirectSignIn: window.location.origin + "/",
  redirectSignOut: window.location.origin + "/",
  responseType: "code", // or 'token', note that REFRESH token will only be generated when the responseType is code
};

const updatedAwsConfig = {
  ...awsConfig,
  Auth: {
    ...awsConfig.Auth,
    oauth: {
      ...oauthSettings,
    },
  },
};

Amplify.configure(updatedAwsConfig);

document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("root")!;
  const root = createRoot(container);
  root.render(
    <BrowserRouter>
      <NotificationContextProvider>
        <ToolsContextProvider>
          <SessionContextProvider>
            <App />
          </SessionContextProvider>
        </ToolsContextProvider>
      </NotificationContextProvider>
    </BrowserRouter>
  );
});
