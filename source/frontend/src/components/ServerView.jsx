/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  Tabs,
  SpaceBetween,
  ColumnLayout,
  Container,
  Box,
  Header
 } from '@awsui/components-react';

import Audit from "../components/ui_attributes/Audit.jsx";
import AllViewerAttributes from '../components/ui_attributes/AllViewerAttributes.jsx'

const ValueWithLabel = ({ label, children }) => (
  <div>
    <Box margin={{ bottom: 'xxxs' }} color="text-label">
      {label}
    </Box>
    <div>{children}</div>
  </div>
);

const ServerView = (props) => {

  function handleOnTabChange(activeTabId) {
    if (props.handleTabChange) {
      props.handleTabChange(activeTabId);
    }
  }

  function selectedTab() {
    if (props.selectedTab) {
      return props.selectedTab;
    }
    else {
      return null;
    }
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


        // <ColumnLayout columns={3}>
        //   <SpaceBetween size="l">
        //     <TextAttribute name="Server Name" value={props.server.server_name}/>
        //   </SpaceBetween>
        // </ColumnLayout>
      },
      {
        label: "Application",
        id: "application",
        content:
        <Container header={<Header variant="h2">Application</Header>}>
          <ColumnLayout columns={3}>
              <SpaceBetween size="l">
                  <AllViewerAttributes
                      schema={props.schema.application}
                      schemas={props.schema}
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
                  schema={props.schema.server}
                  schemas={props.schema}
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
