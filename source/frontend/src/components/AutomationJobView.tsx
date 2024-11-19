// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { ColumnLayout, Container, Header, SpaceBetween, Tabs, Textarea } from "@cloudscape-design/components";

import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import Audit from "./ui_attributes/Audit";

const AutomationJobView = (props) => {
  function handleOnTabChange(activeTabId) {
    if (props.handleTabChange) {
      props.handleTabChange(activeTabId);
    }
  }

  function selectedTab() {
    if (props.selectedTab) {
      return props.selectedTab;
    } else {
      return null;
    }
  }

  return (
    <Tabs
      activeTabId={selectedTab()}
      onChange={({ detail }) => handleOnTabChange(detail.activeTabId)}
      tabs={[
        {
          label: "Details",
          id: "details",
          content: (
            <Container header={<Header variant="h2">Details</Header>}>
              <ColumnLayout columns={2} variant="text-grid">
                <SpaceBetween size="l">
                  <AllViewerAttributes
                    schema={props.schema}
                    schemas={props.schemas}
                    item={props.item}
                    dataAll={props.dataAll}
                  />
                  <Audit item={props.item} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
        {
          label: "Log",
          id: "log",
          content: (
            <Container header={<Header variant="h2">Log</Header>}>
              <Textarea value={props.item.output} rows={12} readOnly />
            </Container>
          ),
        },
      ]}
    />
  );
};

export default AutomationJobView;
