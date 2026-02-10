/* eslint-disable */
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
	 
import React from "react";
import { ColumnLayout, Container, Header, SpaceBetween, Tabs } from "@cloudscape-design/components";

import Audit from "../components/ui_attributes/Audit";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import ItemTable from "./ItemTable";
import { ValueWithLabel } from "./ui_attributes/ValueWithLabel";
import { EntitySchema } from "../models/EntitySchema";
import { Schemas } from "../utils/Constants";

type WPMJobViewParams = {
  handleTabChange: (arg0: string) => void;
  selectedTab: any;
  wpm_job: { wpm_job_name: string; wpm_job_id?: string };
  schemas: Record<string, EntitySchema>;
  dataAll: any;
};
const WPMJobView = (props: WPMJobViewParams) => {
  function handleOnTabChange(activeTabId: string) {
    if (props.handleTabChange) {
      props.handleTabChange(activeTabId);
    }
  }

  function selectedTab() {
    return props.selectedTab;
  }

  const relatedWaves = props.dataAll?.wave?.data?.filter((wave: any) => 
    wave.wpm_job_id === props.wpm_job.wpm_job_id
  ) || [];

  const relatedMoveGroups = props.dataAll?.move_group?.data?.filter((group: any) => 
    group.wpm_job_id === props.wpm_job.wpm_job_id
  ) || [];

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
                  <ValueWithLabel label="WPM Job Name">{props.wpm_job.wpm_job_name}</ValueWithLabel>
                  <Audit item={props.wpm_job} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
        {
          label: "Waves",
          id: "waves",
          content: (
            <ItemTable
              schema={props.schemas.wave}
              schemaKeyAttribute={Schemas.Wave.keyAttribute}
              schemaName={Schemas.Wave.name}
              dataAll={props.dataAll}
              items={relatedWaves}
              isLoading={props.dataAll.wave.isLoading}
              errorLoading={props.dataAll.wave.error}
              provideLink={true}
            />
          ),
        },
        {
          label: "Groups",
          id: "groups",
          content: (
            <ItemTable
              schema={props.schemas.move_group}
              schemaKeyAttribute={Schemas.MoveGroup.keyAttribute}
              schemaName={Schemas.MoveGroup.name}
              dataAll={props.dataAll}
              items={relatedMoveGroups}
              isLoading={props.dataAll.move_group.isLoading}
              errorLoading={props.dataAll.move_group.error}
              provideLink={true}
            />
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
                    schema={props.schemas.wpm_job}
                    schemas={props.schemas}
                    item={props.wpm_job}
                    dataAll={props.dataAll}
                  />
                </ColumnLayout>
                <Audit item={props.wpm_job} expanded={true} />
              </SpaceBetween>
            </Container>
          ),
        },
      ]}
      // variant="container"
    />
  );
};

export default WPMJobView;