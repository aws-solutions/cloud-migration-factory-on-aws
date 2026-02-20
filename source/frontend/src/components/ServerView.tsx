/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { ColumnLayout, Container, Header, SpaceBetween, Tabs } from "@cloudscape-design/components";

import Audit from "../components/ui_attributes/Audit";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import { ValueWithLabel } from "./ui_attributes/ValueWithLabel";
import { Application, Database, DataLoadingState, EntitySchema, MoveGroup, Server, Wave, WPMJob } from "../models";

type ServerViewDataAll = {
  readonly app: DataLoadingState<Application>;
  readonly database: DataLoadingState<Database>;
  readonly server: DataLoadingState<Server>;
  readonly move_group: DataLoadingState<MoveGroup>;
  readonly wave: DataLoadingState<Wave>;
  readonly wpm_job: DataLoadingState<WPMJob>;
};

type ServerViewParams = {
  readonly handleTabChange: (arg0: string) => void;
  readonly selectedTab: string;
  readonly server: Server;
  readonly schemas: Record<string, EntitySchema>;
  readonly dataAll: ServerViewDataAll;
};

const ServerView = (props: ServerViewParams) => {
  return (
    <Tabs
      activeTabId={props.selectedTab}
      onChange={({ detail }) => props.handleTabChange(detail.activeTabId)}
      tabs={[
        {
          label: "Details",
          id: "details",
          content: (
            <Container header={<Header variant="h2">Details</Header>}>
              <ColumnLayout columns={2} variant="text-grid">
                <SpaceBetween size="l">
                  <ValueWithLabel label="Server Name">{props.server.server_name}</ValueWithLabel>
                  <Audit item={props.server} expanded={true} />
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
              <SpaceBetween size="l">
                <ColumnLayout columns={2} variant="text-grid">
                  <AllViewerAttributes
                    schema={props.schemas.server}
                    schemas={props.schemas}
                    item={props.server}
                    dataAll={props.dataAll}
                  />
                </ColumnLayout>
                <Audit item={props.server} expanded={true} />
              </SpaceBetween>
            </Container>
          ),
        },
      ]}
      // variant="container"
    />
  );
};

export default ServerView;
