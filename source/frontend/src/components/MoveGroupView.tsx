/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { ColumnLayout, Container, Header, SpaceBetween, Tabs } from "@cloudscape-design/components";

import TextAttribute from "../components/ui_attributes/TextAttribute";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import ItemTable from "./ItemTable";
import Audit from "./ui_attributes/Audit";
import { Application, DataLoadingState, EntitySchema, Server, MoveGroup, Wave, WPMJob } from "../models";
import { Schemas } from "../utils/Constants";

type MoveGroupDetailsViewParams = {
  readonly schemas: Record<string, EntitySchema>;
  readonly selectedItems: MoveGroup[];
  readonly dataAll: {
    readonly app: DataLoadingState<Application>;
    readonly server: DataLoadingState<Server>;
    readonly wpm_job: DataLoadingState<WPMJob>;
    readonly wave: DataLoadingState<Wave>;
  };
  handleTabChange: (arg0: string) => void;
  selectedTab: string;
};

export const MoveGroupDetailsView = ({
  dataAll,
  schemas,
  selectedItems,
  handleTabChange,
  selectedTab,
}: MoveGroupDetailsViewParams) => {
  if (selectedItems.length !== 1) return <></>;
  const selectedMoveGroup = selectedItems[0];
  const selectedMoveGroupId = selectedMoveGroup.move_group_id;

  // Filter apps that belong to this move group
  const appsForCurrentMoveGroup = dataAll.app.data.filter(
    (app) => selectedMoveGroup.app_ids && selectedMoveGroup.app_ids.includes(app.app_id)
  );

  // Filter servers that belong to this move group
  const serversForCurrentMoveGroup = dataAll.server.data.filter(
    (server) => selectedMoveGroup.server_ids && selectedMoveGroup.server_ids.includes(server.server_id)
  );

  // Filter waves related to this move group
  const wavesForCurrentMoveGroup = dataAll.wave.data.filter((wave) => selectedMoveGroup.wave_id === wave.wave_id);

  // Filter jobs related to this move group
  const wpmjobsForCurrentMoveGroup = dataAll.wpm_job.data.filter(
    (job) => job?.move_group_ids && job?.move_group_ids.includes(selectedMoveGroupId)
  );

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
                  <TextAttribute label="Move Group Name">{selectedMoveGroup.move_group_name}</TextAttribute>
                  <TextAttribute label="Move Group ID">{selectedMoveGroup.move_group_id}</TextAttribute>
                  <TextAttribute label="Wave ID">{selectedMoveGroup.wave_id || "Not assigned"}</TextAttribute>
                  <TextAttribute label="WPM Job ID">{selectedMoveGroup.wpm_job_id || "Not assigned"}</TextAttribute>
                  <TextAttribute label="Server Count">{selectedMoveGroup.server_count}</TextAttribute>
                  <TextAttribute label="Total Server Storage">
                    {selectedMoveGroup.total_server_storage} GB
                  </TextAttribute>
                  <TextAttribute label="Complexity Score">{selectedMoveGroup.complexity_score}</TextAttribute>
                  <Audit item={selectedMoveGroup} expanded={true} />
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
              items={serversForCurrentMoveGroup}
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
              items={appsForCurrentMoveGroup}
              isLoading={dataAll.app.isLoading}
              errorLoading={dataAll.app.error}
              provideLink={true}
            />
          ),
        },
        {
          label: "Waves",
          id: "waves",
          content: (
            <ItemTable
              schema={schemas.wave}
              schemaKeyAttribute={Schemas.Wave.keyAttribute}
              schemaName={Schemas.Wave.name}
              dataAll={dataAll}
              items={wavesForCurrentMoveGroup}
              isLoading={dataAll.wave.isLoading}
              errorLoading={dataAll.wave.error}
              provideLink={true}
            />
          ),
        },
        {
          label: "WPM Jobs",
          id: "wpm_jobs",
          content: (
            <ItemTable
              schema={schemas.wpm_job}
              schemaKeyAttribute={Schemas.WPMJob.keyAttribute}
              schemaName={Schemas.WPMJob.name}
              dataAll={dataAll}
              items={wpmjobsForCurrentMoveGroup}
              isLoading={dataAll.wpm_job.isLoading}
              errorLoading={dataAll.wpm_job.error}
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
                  <AllViewerAttributes
                    schemas={schemas}
                    schema={schemas.move_group}
                    item={selectedMoveGroup}
                    dataAll={dataAll}
                  />
                  <Audit item={selectedMoveGroup} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
      ]}
    />
  );
};
