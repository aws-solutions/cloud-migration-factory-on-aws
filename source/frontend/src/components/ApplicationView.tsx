// @ts-nocheck
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
  Header
 } from '@awsui/components-react';

import TextAttribute from '../components/ui_attributes/TextAttribute'
import AllViewerAttributes from '../components/ui_attributes/AllViewerAttributes'
import ItemTable from './ItemTable'
import Audit from "./ui_attributes/Audit";

const ApplicationView = (props) => {

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
        content:
        <Container header={<Header variant="h2">Details</Header>}>
          <ColumnLayout columns={2}>
            <SpaceBetween size="l">
              <TextAttribute label="Application Name">{props.app.app_name}</TextAttribute>
              <TextAttribute label="Wave">{props.app.wave_id ? props.app.wave_id : '-'}</TextAttribute>
              <Audit item={props.app} expanded={true}/>
            </SpaceBetween>
          </ColumnLayout>
        </Container>
      },
      {
        label: "Servers",
        id: "servers",
        content:
          <ItemTable
            schema={props.schema.server}
            schemaName={'server'}
            schemaKeyAttribute={'server_id'}
            items={props.servers.items}
            dataAll={props.dataAll}
            isLoading={props.servers.isLoading}
            errorLoading={props.servers.error}
            provideLink={true}
            />
      },
      {
        label: "Wave",
        id: "wave",
        content:
        <Container header={<Header variant="h2">Wave</Header>}>
          <ColumnLayout columns={2}>
            <SpaceBetween size="l">
              <AllViewerAttributes
                  schema={props.schema.wave}
                  schemas={props.schema}
                  item={props.wave}
                  dataAll={props.dataAll}
              />
              <Audit item={props.wave} expanded={true}/>
            </SpaceBetween>
          </ColumnLayout>
        </Container>
      },
      {
        label: "All attributes",
        id: "attributes",
        content:
        <Container header={<Header variant="h2">All attributes</Header>}>
          <ColumnLayout columns={2} variant="text-grid">
              <SpaceBetween size="l">
                <AllViewerAttributes
                  schema={props.schema.application}
                  schemas={props.schema}
                  item={props.app}
                  dataAll={props.dataAll}
                />
                <Audit item={props.app} expanded={true}/>
              </SpaceBetween>
          </ColumnLayout>
        </Container>
      }
    ]}
  />;
};

export default ApplicationView;
