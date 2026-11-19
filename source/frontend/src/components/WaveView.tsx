/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { ColumnLayout, Container, Header, SpaceBetween, Tabs } from "@cloudscape-design/components";

import TextAttribute from "../components/ui_attributes/TextAttribute";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import ItemTable from "./ItemTable";
import Audit from "./ui_attributes/Audit";
import { DataLoadingState, EntitySchema, Application, Server, Job, Wave } from "../models";
import { Schemas } from "../utils/Constants";

type WaveDetailsViewParams = {
  readonly schemas: Record<string, EntitySchema>;
  readonly selectedItems: Wave[];
  readonly dataAll: {
    readonly app: DataLoadingState<Application>;
    readonly server: DataLoadingState<Server>;
    readonly job: DataLoadingState<Job>;
  };
  readonly handleTabChange: (tabId: string) => void;
  readonly selectedTab: string;
};

export const WaveDetailsView = ({
  dataAll,
  schemas,
  selectedItems,
  handleTabChange,
  selectedTab,
}: WaveDetailsViewParams) => {
  if (selectedItems.length !== 1) return <></>;

  const selectedWave = selectedItems[0];
  const selectedWaveId = selectedWave.wave_id;

  const appsForCurrentWave = dataAll.app.data.filter((app) => app.wave_ids?.includes(selectedWaveId));

  const serversForCurrentWave = dataAll.server.data.filter((server) => server.wave_id === selectedWaveId);

  const jobsForCurrentWave = dataAll.job.data.filter((job) => job.script.script_arguments?.Waveid === selectedWaveId);

  return (
    <Tabs
      activeTabId={selectedTab}
      onChange={({ detail }) => handleTabChange(detail.activeTabId)}
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
              schemaKeyAttribute={Schemas.Server.keyAttribute}
              schemaName={Schemas.Server.name}
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
              schemaKeyAttribute={Schemas.Application.keyAttribute}
              schemaName={Schemas.Application.name}
              dataAll={dataAll}
              items={appsForCurrentWave}
              isLoading={dataAll.app.isLoading}
              errorLoading={dataAll.app.error}
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
