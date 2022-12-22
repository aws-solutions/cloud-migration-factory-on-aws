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

const PermissionsView = (props) => {

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
    tabs={props.itemType === 'roles' ?
      [
        {
          label: "Details",
          id: "details",
          content: <Container header={<Header variant="h2">Details</Header>}>
                    <ColumnLayout columns={2} variant="text-grid">
                      <SpaceBetween size="l">
                          <AllViewerAttributes
                            schema={props.schema}
                            schemas={props.schemas}
                            item={props.item}
                          />
                          <Audit item={props.item} expanded={true}/>
                      </SpaceBetween>
                    </ColumnLayout>
                  </Container>


          // <ColumnLayout columns={3}>
          //   <SpaceBetween size="l">
          //     <TextAttribute name="Server Name" value={props.server.server_name}/>
          //   </SpaceBetween>
          // </ColumnLayout>
        }
      ]
      :
      [
        {
          label: "Details",
          id: "details",
          content: <Container header={<Header variant="h2">Details</Header>}>
            <ColumnLayout columns={2} variant="text-grid">
              <SpaceBetween size="l">
                <AllViewerAttributes
                  schema={props.schema}
                  schemas={props.schemas}
                  item={props.item}
                />
                <Audit item={props.item} expanded={true}/>
              </SpaceBetween>
            </ColumnLayout>
          </Container>


          // <ColumnLayout columns={3}>
          //   <SpaceBetween size="l">
          //     <TextAttribute name="Server Name" value={props.server.server_name}/>
          //   </SpaceBetween>
          // </ColumnLayout>
        }
      ]
    }
    // variant="container"
  />;
};

export default PermissionsView;
