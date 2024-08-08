/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from "react";
import { ColumnLayout, Container, Header, SpaceBetween, Tabs } from "@awsui/components-react";

import TextAttribute from "../components/ui_attributes/TextAttribute";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import ItemTable from "./ItemTable";
import Audit from "./ui_attributes/Audit";
import { DataLoadingState, EntitySchema } from "../models/EntitySchema";
import { Application } from "../models/Application";
import { Server } from "../models/Server";

type WaveDetailsViewParams = {
  schemas: Record<string, EntitySchema>;
  selectedItems: any[];
  dataAll: {
    application: DataLoadingState<Application>;
    server: DataLoadingState<Server>;
    job: DataLoadingState<any>;
  };
};

export const WaveDetailsView = ({ dataAll, schemas, selectedItems }: WaveDetailsViewParams) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState("details");

  if (selectedItems.length !== 1) return <></>;
  const selectedWave = selectedItems[0];
  const selectedWaveId = selectedWave.wave_id;

  const appsForCurrentWave = dataAll.application.data.filter((app) => app.wave_id === selectedWaveId);

  const serversForCurrentWave = appsForCurrentWave.flatMap((app) =>
    dataAll.server.data.filter((server) => server.app_id === app.app_id)
  );

  const jobsForCurrentWave = dataAll.job.data.filter((job) => job.script.script_arguments?.Waveid === selectedWaveId);

  return (
    <Tabs
      activeTabId={viewerCurrentTab}
      onChange={({ detail }) => setViewerCurrentTab(detail.activeTabId)}
      tabs={[
        {
          label: "Details",
          id: "details",
          content: (
            <Container header={<Header variant="h2">Details</Header>}>
              <ColumnLayout columns={2}>
                <SpaceBetween size="l">
                  <TextAttribute label="Wave Name">{selectedWave.wave_name}</TextAttribute>
                  <TextAttribute label="Wave ID">{selectedWave.wave_id}</TextAttribute>
                  <Audit item={selectedWave} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
        {
          label: "Servers",
          id: "servers",
          content: (
            <ItemTable
              schema={schemas.server}
              schemaKeyAttribute={"server_id"}
              schemaName={"server"}
              dataAll={dataAll}
              items={serversForCurrentWave}
              isLoading={dataAll.server.isLoading}
              errorLoading={dataAll.server.error}
              provideLink={true}
            />
          ),
        },
        {
          label: "Applications",
          id: "applications",
          content: (
            <ItemTable
              schema={schemas.application}
              schemaKeyAttribute={"app_id"}
              schemaName={"application"}
              dataAll={dataAll}
              items={appsForCurrentWave}
              isLoading={dataAll.application.isLoading}
              errorLoading={dataAll.application.error}
              provideLink={true}
            />
          ),
        },
        {
          label: "Jobs",
          id: "jobs",
          content: (
            <ItemTable
              schema={schemas.job}
              schemaKeyAttribute={"uuid"}
              schemaName={"job"}
              dataAll={dataAll}
              items={jobsForCurrentWave}
              isLoading={dataAll.job.isLoading}
              errorLoading={dataAll.job.error}
              provideLink={true}
            />
          ),
        },
        {
          label: "All attributes",
          id: "attributes",
          content: (
            <Container header={<Header variant="h2">All attributes</Header>}>
              <ColumnLayout columns={2}>
                <SpaceBetween size="l">
                  <AllViewerAttributes schemas={schemas} schema={schemas.wave} item={selectedWave} dataAll={dataAll} />
                  <Audit item={selectedWave} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
      ]}
    />
  );
};
