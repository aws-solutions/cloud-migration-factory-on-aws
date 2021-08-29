import React from "react";
import { Route, Switch } from "react-router-dom";
import User from "./containers/User";
import UserApps from "./containers/UserApps";
import UserServers from "./containers/UserServers";
import UserWaves from "./containers/UserWaves";
import ToolsCE from "./containers/ToolsCloudEndure";
import ToolsAMS from "./containers/ToolsAMS";
import ToolsMGN from "./containers/ToolsMGN";
import NotFound from "./containers/NotFound";
import Login from "./containers/Login";
import AppliedRoute from "./components/AppliedRoute";
import AdminStage from "./containers/AdminStage";
import AdminAttribute from "./containers/AdminAttribute";
import AdminRole from "./containers/AdminRole";
import ForgotPassword from "./containers/ForgotPassword";
import ChangePassword from "./containers/ChangePassword";

export default ({ childProps }) =>
  <Switch>
    <AppliedRoute path="/" exact component={User} props={childProps} />
    <AppliedRoute path="/tools/mgn" exact component={ToolsMGN} props={childProps} />
    <AppliedRoute path="/tools/cloudendure" exact component={ToolsCE} props={childProps} />
    <AppliedRoute path="/tools/ams" exact component={ToolsAMS} props={childProps} />
    <AppliedRoute path="/apps" exact component={UserApps} props={childProps} />
    <AppliedRoute path="/servers" exact component={UserServers} props={childProps} />
    <AppliedRoute path="/waves" exact component={UserWaves} props={childProps} />
    <AppliedRoute path="/login" exact component={Login} props={childProps} />
    <AppliedRoute path="/admin/stage" exact component={AdminStage} props={childProps} />
    <AppliedRoute path="/admin/attribute" exact component={AdminAttribute} props={childProps} />
    <AppliedRoute path="/admin/role" exact component={AdminRole} props={childProps} />
    <AppliedRoute path="/forgot/pwd" exact component={ForgotPassword} props={childProps} />
    <AppliedRoute path="/change/pwd" exact component={ChangePassword} props={childProps} />
    { /* Finally, catch all unmatched routes */ }
    <Route component={NotFound} />
  </Switch>;
