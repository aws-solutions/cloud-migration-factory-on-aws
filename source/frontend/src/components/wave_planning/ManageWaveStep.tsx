/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Container, Header, Modal, SpaceBetween, Tabs, TabsProps } from "@cloudscape-design/components";

import { Application, Database, EntitySchema, MoveGroup, Server, UserAccess, Wave, WPMAllData } from "../../models";
import { Schemas } from "../../utils/Constants";
import ItemTable from "../ItemTable";
import { exportTable } from "../../utils/xlsx-export";
import TransferList from "./TransferList";
import ERDiagram from "./ERDiagram";
import { ReadOnlyAlert } from "./JobWizard.util";

export interface ManageWaveStepProps {
  readonly userAccess?: UserAccess;
  readonly readOnly?: boolean;
  readonly schemas: Record<string, EntitySchema>;
  readonly dataAll: WPMAllData;
  readonly isLoading: boolean;
  readonly applications: Application[];
  readonly databases: Database[];
  readonly servers: Server[];
  readonly moveGroups: MoveGroup[];
  readonly waves: Wave[];
  readonly onConfirm: (waves: Wave[], moveGroups: MoveGroup[]) => void | Promise<void>;
}

const ManageWaveStep = (props: ManageWaveStepProps) => {
  // Memorize a UserAccess object with readonly permission for Wave
  // so as to disable the edit in ItemAmend and ItemTable components
  const readOnlyUserAccess = React.useMemo(
    () => ({
      ...props.userAccess,
      [Schemas.Wave.name]: { read: true },
    }),
    [props.userAccess]
  );

  const { applications, dataAll, isLoading, databases, moveGroups, onConfirm, readOnly, schemas, servers, waves } =
    props;
  const [showTransferList, setShowTransferList] = React.useState<boolean>(false);
  const [selectedWaves, setSelectedWaves] = React.useState<Wave[]>([]);
  const [selectedMoveGroup, setSelectedMoveGroup] = React.useState<MoveGroup>();
  const [showModal, setShowModal] = React.useState<boolean>(false);

  // Refresh selectedWaves to get the new `move_group_ids` attribute updated by TransferList
  React.useEffect(() => {
    setSelectedWaves(
      selectedWaves.map((sw) => waves.find((w) => w.wave_id === sw.wave_id)).filter((w): w is Wave => !!w)
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [waves]);

  const handleDownloadItems = React.useCallback(() => {
    const sheetName = "Waves";
    exportTable(selectedWaves.length ? selectedWaves : waves, sheetName, sheetName.toLowerCase());
  }, [selectedWaves, waves]);

  const handleEditItem = React.useCallback(() => {
    setShowTransferList(true);
  }, []);

  const handleMoveGroupSelect = React.useCallback((mg: MoveGroup) => {
    setSelectedMoveGroup(mg);
    setShowModal(true);
  }, []);

  const [selectedWave] = selectedWaves;

  return (
    <>
      <SpaceBetween size={"xl"} direction={"vertical"}>
        {readOnly ? <ReadOnlyAlert /> : undefined}
        <ItemTable
          userAccess={readOnly ? readOnlyUserAccess : props.userAccess}
          dataAll={dataAll}
          editButtonText="Manage Move Groups"
          errorLoading={""}
          isLoading={isLoading}
          items={waves}
          handleDownloadItems={handleDownloadItems}
          handleEditItem={handleEditItem}
          schema={schemas[Schemas.Wave.name]}
          schemaName={Schemas.Wave.name}
          schemaKeyAttribute={Schemas.Wave.keyAttribute}
          selectedItems={selectedWaves}
          selectionType={"single"}
          handleSelectionChange={(selectedItems) => setSelectedWaves(selectedItems)}
        />
        {selectedWaves.length > 0 && (
          <ChildrenTabs
            applications={applications}
            dataAll={dataAll}
            isLoading={isLoading}
            databases={databases}
            moveGroups={moveGroups}
            schemas={schemas}
            servers={servers}
            waves={waves}
            selectedWaves={selectedWaves}
            onMoveGroupSelection={handleMoveGroupSelect}
          />
        )}
      </SpaceBetween>
      <Modal
        header={<Header>Manage Move Groups in Waves</Header>}
        onDismiss={() => setShowTransferList(false)}
        size={"max"}
        visible={showTransferList}
      >
        {/* Force re-render each time model shows */}
        {showTransferList && selectedWave ? (
          <TransferList
            header={
              <Header
                variant="h3"
                description="Add or remove groups to migrate from a list of unassigned or assigned groups in pending jobs."
              >
                Manage Waves
              </Header>
            }
            parent={{
              records: waves,
              labelAttribute: "wave_name",
              valueAttribute: "wave_id",
              selectedValue: selectedWave.wave_id,
              multivalueRelationshipAttribute: "move_group_ids",
            }}
            child={{
              schemaName: Schemas.MoveGroup.name,
              schema: schemas[Schemas.MoveGroup.name],
              records: moveGroups,
              valueAttribute: "move_group_id",
            }}
            onCancel={() => setShowTransferList(false)}
            onConfirm={({ parents, children }) =>
              Promise.resolve(onConfirm(parents, children)).then(() => setShowTransferList(false))
            }
            customLabels={{
              sourceHeader: "Move Groups in selected Wave",
              sourceButtonText: "Remove from Wave",
              targetHeader: "Available Move Groups",
              targetButtonText: "Add to Wave",
            }}
          />
        ) : undefined}
      </Modal>
      <Modal
        header={selectedMoveGroup?.move_group_name}
        onDismiss={() => setShowModal(false)}
        size={"max"}
        visible={showModal}
      >
        <ChildrenTabs
          applications={applications}
          dataAll={dataAll}
          isLoading={isLoading}
          databases={databases}
          moveGroups={moveGroups}
          schemas={schemas}
          servers={servers}
          waves={waves}
          selectedMoveGroup={selectedMoveGroup}
          hiddenTabs={[Schemas.MoveGroup.name, "entity_visualization"]}
        />
      </Modal>
    </>
  );
};

interface ChildrenTabsProps extends Omit<ManageWaveStepProps, "userAccess" | "onConfirm"> {
  readonly hiddenTabs?: string[];
  readonly dataAll: WPMAllData;
  readonly selectedWaves?: Wave[];
  readonly selectedMoveGroup?: MoveGroup;
  readonly onMoveGroupSelection?: (moveGroup: MoveGroup) => void;
}

const ChildrenTabs = ({
  applications,
  dataAll,
  isLoading,
  databases,
  servers,
  moveGroups,
  hiddenTabs,
  selectedWaves,
  selectedMoveGroup,
  onMoveGroupSelection,
  schemas,
}: ChildrenTabsProps) => {
  const visibleMoveGroups = React.useMemo(
    () =>
      onMoveGroupSelection
        ? moveGroups.filter((mg: MoveGroup) =>
            selectedWaves?.some((wave) => wave.move_group_ids?.includes(mg.move_group_id))
          )
        : selectedMoveGroup
          ? [selectedMoveGroup]
          : [],
    [moveGroups, onMoveGroupSelection, selectedMoveGroup, selectedWaves]
  );

  const visibleApplications = React.useMemo(
    () => applications.filter((app) => visibleMoveGroups.some((mg) => app.move_group_ids?.includes(mg.move_group_id))),
    [visibleMoveGroups, applications]
  );

  const visibleServers = React.useMemo(
    () => servers.filter((svr) => visibleMoveGroups.some((mg) => svr.move_group_id === mg.move_group_id)),
    [visibleMoveGroups, servers]
  );

  const visibleDatabases = React.useMemo(
    () => databases.filter((db) => visibleMoveGroups.some((mg) => db.move_group_id === mg.move_group_id)),
    [visibleMoveGroups, databases]
  );

  const [localSelectedMoveGroup, setLocalSelectedMoveGroup] = React.useState<MoveGroup>();

  const tabs: TabsProps["tabs"] = React.useMemo(
    () =>
      [
        {
          label: `${Schemas.MoveGroup.friendlyName}s`,
          id: Schemas.MoveGroup.name,
          content: (
            <ItemTable
              description={"Click on each group to view the applications, servers and databases belong to this group."}
              dataAll={dataAll}
              isLoading={isLoading}
              errorLoading={""}
              items={visibleMoveGroups}
              schema={schemas[Schemas.MoveGroup.name]}
              schemaName={Schemas.MoveGroup.name}
              schemaKeyAttribute={Schemas.MoveGroup.keyAttribute}
              selectedItems={localSelectedMoveGroup ? [localSelectedMoveGroup] : []}
              selectionType={"single"}
              handleSelectionChange={(items: MoveGroup[]) => {
                setLocalSelectedMoveGroup(items[0]);
                onMoveGroupSelection?.(items[0]);
              }}
            />
          ),
        },
        {
          label: `${Schemas.Application.friendlyName}s`,
          id: Schemas.Application.name,
          content: (
            <ItemTable
              dataAll={dataAll}
              isLoading={isLoading}
              errorLoading={""}
              items={visibleApplications}
              schema={schemas[Schemas.Application.name]}
              schemaName={Schemas.Application.name}
              schemaKeyAttribute={Schemas.Application.keyAttribute}
            />
          ),
        },
        {
          label: `${Schemas.Server.friendlyName}s`,
          id: Schemas.Server.name,
          content: (
            <ItemTable
              dataAll={dataAll}
              isLoading={isLoading}
              errorLoading={""}
              items={visibleServers}
              schema={schemas[Schemas.Server.name]}
              schemaName={Schemas.Server.name}
              schemaKeyAttribute={Schemas.Server.keyAttribute}
            />
          ),
        },
        {
          label: `${Schemas.Database.friendlyName}s`,
          id: Schemas.Database.name,
          content: (
            <ItemTable
              dataAll={dataAll}
              isLoading={isLoading}
              errorLoading={""}
              items={visibleDatabases}
              schema={schemas[Schemas.Database.name]}
              schemaName={Schemas.Database.name}
              schemaKeyAttribute={Schemas.Database.keyAttribute}
            />
          ),
        },
        {
          label: "Entity Visualization",
          id: "entity_visualization",
          content: (
            <Container fitHeight disableContentPaddings>
              <div
                style={{ width: "100%", height: "100%", minHeight: "500px", display: "flex", flexDirection: "column" }}
              >
                <ERDiagram
                  schemas={schemas}
                  isLoading={isLoading}
                  selectedWaves={selectedWaves}
                  moveGroups={moveGroups}
                  applications={applications}
                  databases={databases}
                  servers={servers}
                />
              </div>
            </Container>
          ),
        },
      ].filter((t) => !hiddenTabs?.includes(t.id)),
    [
      applications,
      dataAll,
      databases,
      hiddenTabs,
      isLoading,
      localSelectedMoveGroup,
      moveGroups,
      onMoveGroupSelection,
      schemas,
      selectedWaves,
      servers,
      visibleApplications,
      visibleDatabases,
      visibleMoveGroups,
      visibleServers,
    ]
  );
  return <Tabs tabs={tabs} />;
};

export default React.memo(ManageWaveStep) as typeof ManageWaveStep;
