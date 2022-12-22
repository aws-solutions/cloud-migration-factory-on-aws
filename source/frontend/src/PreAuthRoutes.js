/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Route, Routes } from "react-router-dom";
import Login from "./containers/Login";
import ForgotPassword from "./containers/ForgotPassword";
import ChangePassword from "./containers/ChangePassword";

export default ({ childProps }) => {

  return (

    <Routes>
      <Route
        path="/login"
        element={
          <Login {...childProps} />
        }
      />
      <Route
        path="/forgot/pwd"
        element={
          <ForgotPassword {...childProps}/>
        }
      />
      <Route
        path="/change/pwd"
        element={
          <ChangePassword {...childProps}/>
        }
      />
      { /* Finally, catch all unmatched routes */}
      <Route
        path="/*"
        element={
          <Login {...childProps} />
        }
      />
    </Routes>)
};
