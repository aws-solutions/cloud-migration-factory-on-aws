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

const DatabaseView = (props) => {

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
                        <ValueWithLabel label="Databse Name">{props.database.database_name}</ValueWithLabel>
                        <Audit item={props.database} expanded={true}/>
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
        label: "All attributes",
        id: "attributes",
        content:
        <Container header={<Header variant="h2">All attributes</Header>}>
          <ColumnLayout columns={2} variant="text-grid">
            <SpaceBetween size="l">
                <AllViewerAttributes
                  schema={props.schema.database}
                  schemas={props.schema}
                  item={props.database}
                  dataAll={props.dataAll}
                />
                <Audit item={props.database} expanded={true}/>
            </SpaceBetween>
          </ColumnLayout>
        </Container>
      }
    ]}
    // variant="container"
  />;
};

export default DatabaseView;
