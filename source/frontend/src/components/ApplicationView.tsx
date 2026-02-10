/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { ColumnLayout, Container, Header, SpaceBetween, Tabs } from "@cloudscape-design/components";

import TextAttribute from "../components/ui_attributes/TextAttribute";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import Audit from "./ui_attributes/Audit";
import { Application, Database, DataLoadingState, EntitySchema, MoveGroup, Server, Wave } from "../models";

export type ApplicationViewDataAll = {
  readonly app: DataLoadingState<Application>;
  readonly database: DataLoadingState<Database>;
  readonly server: DataLoadingState<Server>;
  readonly move_group: DataLoadingState<MoveGroup>;
  readonly wave: DataLoadingState<Wave>;
  // Custom assets
  readonly [key: string]: DataLoadingState<unknown>;
};

type ApplicationViewParams = {
  handleTabChange: (arg0: string) => void;
  selectedTab: string;
  schemas: Record<string, EntitySchema>;
  dataAll: ApplicationViewDataAll;
  app: Application;
};
const ApplicationView = ({ handleTabChange, selectedTab, schemas, dataAll, app }: ApplicationViewParams) => {
  return (
    <Tabs
      activeTabId={selectedTab}
      onChange={({ detail }) => handleTabChange(detail.activeTabId)}
      tabs={[
        {
          label: "Details",
          id: "details",
          content: (
            <Container header={<Header variant="h2">Details</Header>}>
              <ColumnLayout columns={2}>
                <SpaceBetween size="l">
                  <TextAttribute label="Application Name">{app.app_name}</TextAttribute>
                  <TextAttribute label="Waves">{app.wave_ids?.length ? app.wave_ids.join() : "-"}</TextAttribute>
                  <Audit item={app} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
        {
          label: "All attributes",
          id: "attributes",
          content: (
            <Container header={<Header variant="h2">All attributes</Header>}>
              <ColumnLayout columns={2} variant="text-grid">
                <SpaceBetween size="l">
                  <AllViewerAttributes schema={schemas.application} schemas={schemas} item={app} dataAll={dataAll} />
                  <Audit item={app} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
      ]}
    />
  );
};

export default ApplicationView;
