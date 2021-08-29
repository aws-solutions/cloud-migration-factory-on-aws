import React from 'react';
import ReactDOM from 'react-dom';
import Amplify from "aws-amplify";
import config from "./config";
import App from './App';
import { BrowserRouter as Router } from "react-router-dom";

import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import './main.css';
import '@fortawesome/fontawesome-free/css/all.css'

Amplify.configure({
  Auth: {
    mandatorySignIn: true,
    region: config.cognito.REGION,
    userPoolId: config.cognito.USER_POOL_ID,
    userPoolWebClientId: config.cognito.APP_CLIENT_ID
  },
  API: {
    endpoints: [
      {
        name: "admin",
        endpoint: config.apiGateway.ADMIN,
        region: config.apiGateway.REGION
      },
      {
        name: "user",
        endpoint: config.apiGateway.USER,
        region: config.apiGateway.REGION
      },
      {
        name: "login",
        endpoint: config.apiGateway.LOGIN,
        region: config.apiGateway.REGION
      },
      {
        name: "tools",
        endpoint: config.apiGateway.TOOLS,
        region: config.apiGateway.REGION
      }
    ]
  }
});

ReactDOM.render(
  <Router>
  <App />
  </Router>,
  document.getElementById("root")
);
