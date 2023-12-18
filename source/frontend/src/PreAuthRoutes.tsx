/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import {Route, Routes} from "react-router-dom";
import Login from "./containers/Login";
import ForgotPassword from "./containers/ForgotPassword";
import ChangePassword from "./containers/ChangePassword";
import {CMFTopNavigation} from "./components/CMFTopNavigation";

export const PreAuthApp = () => {
  return <>
    <CMFTopNavigation
      utilities={[{
        type: "menu-dropdown",
        text: "Documentation",
        items: [
          {
            id: "cmf-overview",
            text: "AWS Cloud Migration Factory Solution",
            external: true,
            href: "https://aws.amazon.com/solutions/implementations/cloud-migration-factory-on-aws/"
          },
          {
            id: "lm",
            text: "Guide for AWS large migrations",
            external: true,
            href: "https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/welcome.html"
          }
        ]
      }]}
    />
    <Routes>
      <Route
        path="/login"
        element={
          <Login/>
        }
      />
      <Route
        path="/forgot/pwd"
        element={
          <ForgotPassword/>
        }
      />
      <Route
        path="/change/pwd"
        element={
          <ChangePassword/>
        }
      />
      { /* Finally, catch all unmatched routes */}
      <Route
        path="/*"
        element={
          <Login/>
        }
      />
    </Routes>
    <div id='modal-root'/>
  </>;
};