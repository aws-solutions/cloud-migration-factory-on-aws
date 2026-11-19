/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Box, ContentLayout, Header, Tabs } from "@cloudscape-design/components";
import { useLocation } from "react-router-dom";
import DataSourceTable from "../components/data-source/DataSourcesTable";
import PlanningRulesTable from "../components/planning-rules/PlanningRulesTable";
import { AppChildProps } from "../models";

const AdminWavePlanning = (props: AppChildProps) => {
  const location = useLocation();
  const [activeTab, setActiveTab] = React.useState(location.state?.activeTab || "data-source");

  return (
    <ContentLayout
      header={
        <Box>
          <Header variant="h1">Wave planning control panel</Header>
        </Box>
      }
    >
      <Tabs
        activeTabId={activeTab}
        onChange={({ detail }) => setActiveTab(detail.activeTabId)}
        tabs={[
          {
            label: "Data source",
            id: "data-source",
            content: <DataSourceTable {...props} selectionType="multi" editable={true} />,
          },
          { label: "Planning rules", id: "planning-rules", content: <PlanningRulesTable /> },
        ]}
      />
    </ContentLayout>
  );
};

export default AdminWavePlanning;
