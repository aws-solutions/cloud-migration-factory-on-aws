/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Route, Routes } from "react-router-dom";
import UserTableApps from "./containers/UserTableApps";
import UserServerTable from "./containers/UserTableServers";
import UserDatabaseTable from "./containers/UserTableDatabases";
import UserWaveTable from "./containers/UserTableWaves";
import UserAutomationJobs from "./containers/UserAutomationJobs";
import UserAutomationScripts from "./containers/UserAutomationScripts";
import UserPipelineTable from "./containers/UserTablePipelines";
import UserTablePipelineTemplates from "./containers/UserTablePipelineTemplates";
import UserDashboard from "./containers/UserDashboard";
import UserImport from "./containers/UserImport";
import UserExport from "./containers/UserExport";
import Login from "./containers/Login";
import AdminPermissions from "./containers/AdminPermissions";
import AdminSchemaMgmt from "./containers/AdminSchemaMgmt";
import ChangePassword from "./containers/ChangePassword";
import CredentialManager from "./containers/CredentialManager";
import { AppChildProps } from "./models/AppChildProps";
import { PipelineTemplatesImport } from "./containers/PipelineTemplatesImport.tsx";

export default ({ childProps }: { childProps: AppChildProps }) => {
    const administratorRoutes = () => {
        const adminRoutes = [
            <Route path="/admin/policy" element={<AdminPermissions {...childProps} />} />,
            <Route path="/admin/attribute" element={<AdminSchemaMgmt {...childProps} />} />,
            <Route path="/admin/credential-manager" element={<CredentialManager />} />
        ]

        if (childProps.userGroups && childProps.userGroups.includes('admin')) {
            return adminRoutes;
        } else {
            return null;
        }
    }

  return (
    <Routes>
      <Route path="/" element={<UserDashboard />} />
      <Route path="/applications" element={<UserTableApps {...childProps} />} />
      <Route path="/applications/:id" element={<UserTableApps {...childProps} />} />
      <Route path="/applications/add" element={<UserTableApps {...childProps} />} />
      <Route path="/applications/edit/:id" element={<UserTableApps {...childProps} />} />
      <Route path="/servers" element={<UserServerTable {...childProps} />} />
      <Route path="/servers/:id" element={<UserServerTable {...childProps} />} />
      <Route path="/servers/add" element={<UserServerTable {...childProps} />} />
      <Route path="/servers/edit/:id" element={<UserServerTable {...childProps} />} />
      <Route path="/waves" element={<UserWaveTable {...childProps} />} />
      <Route path="/waves/:id" element={<UserWaveTable {...childProps} />} />
      <Route path="/waves/add" element={<UserWaveTable {...childProps} />} />
      <Route path="/waves/edit/:id" element={<UserWaveTable {...childProps} />} />
      <Route path="/databases" element={<UserDatabaseTable {...childProps} />} />
      <Route path="/databases/:id" element={<UserDatabaseTable {...childProps} />} />
      <Route path="/databases/add" element={<UserDatabaseTable {...childProps} />} />
      <Route path="/databases/edit/:id" element={<UserDatabaseTable {...childProps} />} />
      <Route path="/pipeline_templates" element={<UserTablePipelineTemplates {...childProps} />} />
      <Route path="/pipeline_templates/import" element={<PipelineTemplatesImport {...childProps} />} />
      <Route path="/pipeline_templates/:id" element={<UserTablePipelineTemplates {...childProps} />} />
      <Route path="/pipeline_templates/add" element={<UserTablePipelineTemplates {...childProps} />} />
      <Route path="/pipeline_templates/edit/:id" element={<UserTablePipelineTemplates {...childProps} />} />
      <Route path="/pipeline_templates/duplicate/:id" element={<UserTablePipelineTemplates {...childProps} />} />
      <Route path="/pipelines" element={<UserPipelineTable {...childProps} />} />
      <Route path="/pipelines/:id" element={<UserPipelineTable {...childProps} />} />
      <Route path="/pipelines/add" element={<UserPipelineTable {...childProps} />} />
      <Route path="/pipelines/edit/:id" element={<UserPipelineTable {...childProps} />} />
      <Route path="/import" element={<UserImport {...childProps} />} />
      <Route path="/export" element={<UserExport />} />
      <Route path="/automation/jobs" element={<UserAutomationJobs {...childProps} />} />
      <Route path="/automation/jobs/:id" element={<UserAutomationJobs {...childProps} />} />
      <Route path="/automation/scripts" element={<UserAutomationScripts {...childProps} />} />
      <Route path="/automation/scripts/add" element={<UserAutomationScripts {...childProps} />} />
      <Route path="/login" element={<Login />} />
      <Route path="/change/pwd" element={<ChangePassword />} />
      {administratorRoutes()}
      {/* Finally, catch all unmatched routes */}
      <Route
        element={
          <div style={{ paddingTop: "100px", textAlign: "center" }}>
            <h3>Sorry, page not found!</h3>
          </div>
        }
      />
    </Routes>
  );
};
