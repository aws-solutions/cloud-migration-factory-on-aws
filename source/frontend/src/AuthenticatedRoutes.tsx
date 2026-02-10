/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

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
import UserWPMJobTable from "./containers/UserTableWPMJobs";
import { JobWizard } from "./components/wave_planning/JobWizard";
import AdminWavePlanning from "./containers/AdminWavePlanning.tsx";
import DataSourceWizard from "./components/data-source/DataSourceWizard.tsx";
import UserMoveGroupsTable from "./containers/UserTableMoveGroups.tsx";
import PlanningRuleForm from "./components/planning-rules/PlanningRuleForm.tsx";
import UserTableCustomAssets from "./containers/UserTableCustomAssets.tsx";
import WpmDataImport from "./containers/WpmDataImport.tsx";
import DataImportWizard from "./components/data-source/DataImportWizard.tsx";

const AuthenticatedRoutes = ({ childProps }: { childProps: AppChildProps }) => {
  const administratorRoutes = () => {
    const adminRoutes = [
      <Route path="/admin/policy" key={0} element={<AdminPermissions {...childProps} />} />,
      <Route path="/admin/attribute" key={1} element={<AdminSchemaMgmt {...childProps} />} />,
      <Route path="/admin/credential-manager" key={2} element={<CredentialManager />} />,
    ];

    // Wave planning admin routes
    if (childProps.enabledModules.includes("WPM")) {
      adminRoutes.push(
        <Route path="/admin/wave-planning" key={3} element={<AdminWavePlanning {...childProps} />} />,
        <Route path="/admin/wave-planning/data-source/add" key={4} element={<DataSourceWizard {...childProps} />} />,
        <Route path="/admin/wave-planning/data-source/edit" key={5} element={<DataSourceWizard {...childProps} />} />,
        <Route path="/admin/wave-planning/planning-rules/add" key={6} element={<PlanningRuleForm {...childProps} />} />,
        <Route
          path="/admin/wave-planning/planning-rules/edit/:id"
          key={7}
          element={<PlanningRuleForm {...childProps} />}
        />
      );
    }

    if (childProps.userGroups && childProps.userGroups.includes("admin")) {
      return adminRoutes;
    } else {
      return null;
    }
  };

  const wpmNormalRoutes = () => {
    if (childProps.enabledModules.includes("WPM")) {
      return [
        <Route key="wpm-jobs" path="/wpm_jobs" element={<UserWPMJobTable {...childProps} />} />,
        <Route key="wpm-jobs-id" path="/wpm_jobs/:id" element={<UserWPMJobTable {...childProps} />} />,
        <Route key="wpm-jobs-add" path="/wpm_jobs/add" element={<JobWizard {...childProps} />} />,
        <Route key="wpm-jobs-edit" path="/wpm_jobs/edit/:id" element={<UserWPMJobTable {...childProps} />} />,
        <Route key="wpm-data-import" path="/wave-planning/data-import" element={<WpmDataImport />} />,
        <Route
          key="wpm-data-import-add"
          path="/wave-planning/data-import/add"
          element={<DataImportWizard {...childProps} />}
        />,
      ];
    }
    return null;
  };

  return (
    <Routes>
      <Route path="/" element={<UserDashboard />} />
      <Route path="/apps" element={<UserTableApps {...childProps} />} />
      <Route path="/apps/:id" element={<UserTableApps {...childProps} />} />
      <Route path="/apps/add" element={<UserTableApps {...childProps} />} />
      <Route path="/apps/edit/:id" element={<UserTableApps {...childProps} />} />
      <Route path="/servers" element={<UserServerTable {...childProps} />} />
      <Route path="/servers/:id" element={<UserServerTable {...childProps} />} />
      <Route path="/servers/add" element={<UserServerTable {...childProps} />} />
      <Route path="/servers/edit/:id" element={<UserServerTable {...childProps} />} />
      <Route path="/waves" element={<UserWaveTable {...childProps} />} />
      <Route path="/waves/:id" element={<UserWaveTable {...childProps} />} />
      <Route path="/waves/add" element={<UserWaveTable {...childProps} />} />
      <Route path="/waves/edit/:id" element={<UserWaveTable {...childProps} />} />
      <Route path="/move_groups" element={<UserMoveGroupsTable {...childProps} />} />
      <Route path="/move_groups/:id" element={<UserMoveGroupsTable {...childProps} />} />
      <Route path="/move_groups/add" element={<UserMoveGroupsTable {...childProps} />} />
      <Route path="/move_groups/edit/:id" element={<UserMoveGroupsTable {...childProps} />} />
      <Route path="/databases" element={<UserDatabaseTable {...childProps} />} />
      <Route path="/databases/:id" element={<UserDatabaseTable {...childProps} />} />
      <Route path="/databases/add" element={<UserDatabaseTable {...childProps} />} />
      <Route path="/databases/edit/:id" element={<UserDatabaseTable {...childProps} />} />
      <Route path="/pipeline_templates" element={<UserTablePipelineTemplates {...childProps} />} />
      <Route path="/pipeline_templates/import" element={<PipelineTemplatesImport />} />
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

      {/* Custom Asset Routes */}
      <Route path="/custom/:assetType" element={<UserTableCustomAssets {...childProps} />} />
      <Route path="/custom/:assetType/add" element={<UserTableCustomAssets {...childProps} />} />
      <Route path="/custom/:assetType/edit/:id" element={<UserTableCustomAssets {...childProps} />} />
      <Route path="/custom/:assetType/:id" element={<UserTableCustomAssets {...childProps} />} />

      {wpmNormalRoutes()}
      {administratorRoutes()}
      {/* Finally, catch all unmatched routes */}
      <Route
        path="*"
        element={
          <div style={{ paddingTop: "100px", textAlign: "center" }}>
            <h3>Sorry, page not found!</h3>
          </div>
        }
      />
    </Routes>
  );
};

export default AuthenticatedRoutes;
