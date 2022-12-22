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

import TextAttribute from '../components/ui_attributes/TextAttribute.jsx'
import AllViewerAttributes from '../components/ui_attributes/AllViewerAttributes.jsx'
import ItemTable from './ItemTable.jsx'
import Audit from "./ui_attributes/Audit";


const WaveView = (props) => {

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
              <TextAttribute label="Wave Name">{props.wave.wave_name}</TextAttribute>
              <TextAttribute label="Wave ID">{props.wave.wave_id}</TextAttribute>
              <Audit item={props.wave} expanded={true}/>
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
            schemaKeyAttribute={'server_id'}
            schemaName={'server'}
            dataAll={props.dataAll}
            items={props.servers.items}
            isLoading={props.servers.isLoading}
            errorLoading={props.servers.error}
            handleSelectionChange={props.servers.handleSelectionChange}
            provideLink={true}
            />
      },
      {
        label: "Applications",
        id: "applications",
        content: <ItemTable
          schema={props.schema.application}
          schemaKeyAttribute={'app_id'}
          schemaName={'application'}
          dataAll={props.dataAll}
          items={props.apps.items}
          isLoading={props.apps.isLoading}
          errorLoading={props.apps.error}
          handleSelectionChange={props.apps.handleSelectionChange}
          provideLink={true}
          />
      },
      {
        label: "Jobs",
        id: "jobs",
        content: <ItemTable
          schema={props.schema.job}
          schemaKeyAttribute={'uuid'}
          schemaName={'job'}
          dataAll={props.dataAll}
          items={props.jobs.items}
          isLoading={props.jobs.isLoading}
          errorLoading={props.jobs.error}
          provideLink={true}
        />
      },
      {
        label: "All attributes",
        id: "attributes",
        content:
        <Container header={<Header variant="h2">All attributes</Header>}>
          <ColumnLayout columns={2}>
              <SpaceBetween size="l">
                <AllViewerAttributes
                  schema={props.schema.wave}
                  item={props.wave}
                  dataAll={props.dataAll}
                />
                <Audit item={props.wave} expanded={true}/>
              </SpaceBetween>
          </ColumnLayout>
        </Container>
      }
    ]}
  />;
};

export default WaveView;
