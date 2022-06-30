import React from 'react';
import {
  Tabs,
  SpaceBetween,
  ColumnLayout,
  Container,
  Header
 } from '@awsui/components-react';

import AllViewerAttributes from '../components/ui_attributes/AllViewerAttributes.jsx'
import Audit from "./ui_attributes/Audit";

const AutomationScriptView = (props) => {

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
              <AllViewerAttributes
                  schema={props.schema}
                  item={props.item}
                  dataAll={props.dataAll}
              />
              <Audit item={props.item} expanded={true}/>
            </SpaceBetween>
          </ColumnLayout>
        </Container>
      }
    ]}
  />;
};

export default AutomationScriptView;
