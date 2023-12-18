/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {ColumnLayout, Container, Header, SpaceBetween, Tabs} from '@awsui/components-react';

import Audit from "../components/ui_attributes/Audit";
import AllViewerAttributes from '../components/ui_attributes/AllViewerAttributes'
import {ValueWithLabel} from "./ui_attributes/ValueWithLabel";
import {EntitySchema} from "../models/EntitySchema";


type ServerViewParams = {
  handleTabChange: (arg0: string) => void;
  selectedTab: any;
  server: { server_name: string };
  schemas: Record<string, EntitySchema>;
  app: { items: any[]; };
  dataAll: any;
};
const ServerView = (props: ServerViewParams) => {

  function handleOnTabChange(activeTabId: string) {
    if (props.handleTabChange) {
      props.handleTabChange(activeTabId);
    }
  }

  function selectedTab() {
      return props.selectedTab;
  }

  return <Tabs
    activeTabId={selectedTab()}
    onChange={({ detail }) => handleOnTabChange(detail.activeTabId)}
    tabs={[
      {
        label: "Details",
        id: "details",
        content: <Container header={<Header variant="h2">Details</Header>}>
                  <ColumnLayout columns={2} variant="text-grid">
                    <SpaceBetween size="l">
                        <ValueWithLabel label="Server Name">{props.server.server_name}</ValueWithLabel>
                        <Audit item={props.server} expanded={true}/>
                    </SpaceBetween>
                  </ColumnLayout>
                </Container>
      },
      {
        label: "Application",
        id: "application",
        content:
        <Container header={<Header variant="h2">Application</Header>}>
          <ColumnLayout columns={3}>
              <SpaceBetween size="l">
                  <AllViewerAttributes
                    schema={props.schemas.application}
                    schemas={props.schemas}
                      item={props.app.items[0]}
                      dataAll={props.dataAll}
                  />
                  <Audit item={props.app.items[0]} expanded={true}/>
              </SpaceBetween>
          </ColumnLayout>
        </Container>
      },
      {
        label: "All attributes",
        id: "attributes",
        content:
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
              <Audit item={props.server} expanded={true}/>
            </SpaceBetween>

        </Container>
      }
    ]}
    // variant="container"
  />;
};

export default ServerView;
