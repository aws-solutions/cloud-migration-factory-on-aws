import React from 'react';
import ReactDOM from 'react-dom';
import Amplify from "aws-amplify";
import App from './App';
import "@awsui/global-styles/index.css"
import { BrowserRouter } from 'react-router-dom';

Amplify.configure({
  Auth: {
    mandatorySignIn: true,
    region: window.env.COGNITO_REGION,
    userPoolId: window.env.COGNITO_USER_POOL_ID,
    userPoolWebClientId: window.env.COGNITO_APP_CLIENT_ID
  },
  API: {
    endpoints: [
      {
        name: "admin",
        endpoint: window.env.API_ADMIN,
        region: window.env.API_REGION
      },
      {
        name: "user",
        endpoint: window.env.API_USER,
        region: window.env.API_REGION
      },
      {
        name: "login",
        endpoint: window.env.API_LOGIN,
        region: window.env.API_REGION
      },
      {
        name: "tools",
        endpoint: window.env.API_TOOLS,
        region: window.env.API_REGION
      }
    ]
  }
});

document.addEventListener('DOMContentLoaded', () => {
  ReactDOM.render(
    <BrowserRouter>
      <App />
    </BrowserRouter>,
    document.getElementById("root")
  );
});
