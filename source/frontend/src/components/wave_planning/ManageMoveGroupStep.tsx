/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useState, useCallback, useRef } from "react";
import { SpaceBetween, Tabs, Modal, Header, Container, TabsProps } from "@cloudscape-design/components";
import { exportTable } from "../../utils/xlsx-export";

import ItemTable from "../ItemTable";
import TransferList from "./TransferList";
import UserApiClient from "../../api_clients/userApiClient";
import { NotificationContext } from "../../contexts/NotificationContext";
import { Schemas, MOVE_GROUP_REQUEST_STATUS } from "../../utils/Constants";
import {
  EntitySchema,
  MoveGroup,
  MoveGroupRequest,
  WPMAllData,
  Server,
  Database,
  WPMApplication,
  Application,
  UserAccess,
} from "../../models";
import { Asset, convertToAssets, convertFromAssets } from "./utils/AssetUtils";
import ERDiagram from "./ERDiagram";
import { ReadOnlyAlert } from "./JobWizard.util";

type MoveGroupStepProps = {
  readonly userAccess?: UserAccess;
  readonly readOnly?: boolean;
  readonly schemas: Record<string, EntitySchema>;
  readonly dataAll: WPMAllData;
  readonly errorLoading: string;
  readonly isLoading: boolean;
  readonly moveGroupRequest?: MoveGroupRequest;
  readonly applications: WPMApplication[];
  readonly moveGroups: MoveGroup[];
  readonly setMoveGroupRequest: (request: MoveGroupRequest) => void;
  readonly onConfirm: (moveGroup: MoveGroup, servers: Server[], databases: Database[]) => Promise<void>;
  readonly wpmDatabases: Database[];
  readonly wpmServers: Server[];
  readonly refreshDatabases: () => void;
  readonly refreshServers: () => void;
  readonly refreshApplications: () => void;
  readonly refreshMoveGroups: () => void;
};

const MoveGroupStep = (props: MoveGroupStepProps) => {
  const {
    applications,
    dataAll,
    errorLoading,
    isLoading,
    moveGroups,
    moveGroupRequest,
    schemas,
    onConfirm,
    readOnly,
    refreshApplications,
    refreshDatabases,
    refreshServers,
    refreshMoveGroups,
    setMoveGroupRequest,
    wpmDatabases,
    wpmServers,
  } = props;
  // Memorize a UserAccess object with readonly permission for Wave
  // so as to disable the edit in ItemAmend and ItemTable components
  const readOnlyUserAccess = React.useMemo(
    () => ({
      ...props.userAccess,
      [Schemas.MoveGroup.name]: { read: true },
    }),
    [props.userAccess]
  );

  const [selectedMoveGroups, setSelectedMoveGroups] = useState<Array<MoveGroup>>([]);
  const { addNotification } = useContext(NotificationContext);
  // Ref to track shown notifications
  const shownNotificationsRef = useRef(new Set<string>());
  const refreshAttemptsRef = useRef(0);

  const handleDownloadItems = React.useCallback(() => {
    const sheetName = "MoveGroups";
    exportTable(selectedMoveGroups, sheetName, sheetName.toLowerCase());
  }, [selectedMoveGroups]);

  // State for managing the asset transfer modal
  const [isAssetModalVisible, setIsAssetModalVisible] = useState(false);
  const [allAssets, setAllAssets] = useState<Asset[]>([]);
  const [selectedMoveGroup] = selectedMoveGroups;

  // State for the selected application to show modal
  const [selectedApplication, setSelectedApplication] = useState<Application>();
  const [showChildrenModal, setShowChildrenModal] = React.useState<boolean>(false);

  // Convert servers and databases to assets format
  React.useEffect(() => {
    if (wpmServers && wpmDatabases) {
      const assets = convertToAssets(wpmServers, wpmDatabases);
      setAllAssets(assets);
    }
  }, [wpmServers, wpmDatabases]);

  const handleManageAssets = useCallback(() => {
    if (selectedMoveGroups.length === 1) {
      setIsAssetModalVisible(true);
    }
  }, [selectedMoveGroups]);

  // Handle asset transfer confirmation
  const handleAssetTransferConfirm = useCallback(
    async ({ children }: { parents?: MoveGroup[]; children: Asset[] }) => {
      // Convert assets back to servers and databases
      const { servers, databases } = convertFromAssets(children, wpmServers, wpmDatabases);
      // Call onChange if selectedMoveGroup is not null and onChange exists
      if (selectedMoveGroup) {
        await onConfirm(selectedMoveGroup, servers, databases);
      }

      // Close modal and refresh data
      setIsAssetModalVisible(false);

      // Show success notification
      addNotification({
        type: "success",
        dismissible: true,
        header: "Assets Updated",
        content: "The assets have been successfully reassigned to move groups.",
      });
    },
    [addNotification, onConfirm, selectedMoveGroup, wpmDatabases, wpmServers]
  );

  const handleRefreshMoveGroupRequest = useCallback(async () => {
    if (!props.moveGroupRequest?.move_group_request_id) {
      return;
    }
    const requestId = props.moveGroupRequest.move_group_request_id;
    try {
      const apiUser = new UserApiClient();
      const updatedMoveGroupRequest = await apiUser.getItem(requestId, Schemas.MoveGroupRequest.name);
      setMoveGroupRequest(updatedMoveGroupRequest);
    } catch (e) {
      // Use existing notification context
      if (!shownNotificationsRef.current.has(`${requestId}-timeout`)) {
        addNotification({
          type: "error",
          dismissible: true,
          header: "Failed to refresh move group request",
          content: e instanceof Error ? e.message : "An unexpected error occurred",
        });
        shownNotificationsRef.current.add(`${requestId}-timeout`);
      }
      console.error("Error refreshing move group request:", e);
    }
  }, [props.moveGroupRequest, setMoveGroupRequest, addNotification]);

  // Track if we've already updated groups after completion
  const completedUpdateRef = React.useRef<boolean>(false);

  // Auto-refresh the move group request status every 1 second if it's not completed or failed
  React.useEffect(() => {
    // Handle initial state when data hasn't loaded yet or readOnly
    if (!moveGroupRequest || readOnly) {
      return;
    }

    const requestId = moveGroupRequest.move_group_request_id;
    const notificationKey = `${requestId}-${moveGroupRequest.status}`;

    // Handle failed requests
    if (moveGroupRequest.status === MOVE_GROUP_REQUEST_STATUS.FAILED) {
      if (!shownNotificationsRef.current.has(notificationKey)) {
        addNotification({
          type: "error",
          dismissible: true,
          header: "Move Group Request Failed",
          content: "The move group request could not be processed. Please check your inputs and try again.",
        });
        shownNotificationsRef.current.add(notificationKey);
      }
      return;
    }

    // Handle completed requests
    if (moveGroupRequest.status === MOVE_GROUP_REQUEST_STATUS.COMPLETED) {
      if (!shownNotificationsRef.current.has(notificationKey)) {
        addNotification({
          type: "success",
          dismissible: true,
          header: "Move Group Request Completed",
          content:
            "Your move group request has been successfully processed. Please refresh the Move Group table to see the latest changes.",
        });
        shownNotificationsRef.current.add(notificationKey);
      }
      // Make one final call to fetch all groups, but only once
      if (!completedUpdateRef.current) {
        refreshMoveGroups();
        refreshApplications();
        refreshServers();
        refreshDatabases();
        completedUpdateRef.current = true;
      }
      return;
    }

    // Track refresh attempts and set a timeout
    const maxRefreshAttempts = 10; // Stop after 10 seconds (10 attempts * 1 seconds)

    // Set up interval only for in-progress requests
    const intervalId = setInterval(() => {
      refreshAttemptsRef.current++;

      // Stop refreshing after reaching max attempts
      if (refreshAttemptsRef.current >= maxRefreshAttempts) {
        clearInterval(intervalId);
        if (!shownNotificationsRef.current.has(`${requestId}-timeout`)) {
          addNotification({
            type: "warning",
            dismissible: true,
            header: "Request Taking Longer Than Expected",
            content:
              "The move group request is taking longer than expected. You can manually refresh to check its status.",
          });
          shownNotificationsRef.current.add(`${requestId}-timeout`);
        }
        return;
      }

      handleRefreshMoveGroupRequest();
      refreshMoveGroups();
    }, 1000);

    return () => clearInterval(intervalId);
  }, [
    addNotification,
    handleRefreshMoveGroupRequest,
    moveGroupRequest,
    readOnly,
    refreshApplications,
    refreshDatabases,
    refreshMoveGroups,
    refreshServers,
  ]);

  const handleApplicationSelectToShowModal = React.useCallback((app: Application) => {
    setSelectedApplication(app);
    setShowChildrenModal(true);
  }, []);

  return (
    <SpaceBetween size={"xl"} direction={"vertical"}>
      {readOnly ? <ReadOnlyAlert /> : undefined}
      <ItemTable
        userAccess={readOnly ? readOnlyUserAccess : props.userAccess}
        items={moveGroups.filter((group: MoveGroup) => moveGroupRequest?.move_group_ids?.includes(group.move_group_id))}
        schema={props.schemas.move_group}
        schemaName={Schemas.MoveGroup.name}
        schemaKeyAttribute={Schemas.MoveGroup.keyAttribute}
        dataAll={dataAll}
        errorLoading={errorLoading}
        isLoading={isLoading}
        handleDownloadItems={handleDownloadItems}
        handleEditItem={handleManageAssets}
        editButtonText="Manage Assets"
        handleRefreshClick={refreshMoveGroups}
        selectionType="single"
        selectedItems={selectedMoveGroups}
        handleSelectionChange={(selectedItems) => setSelectedMoveGroups(selectedItems)}
      />

      {selectedMoveGroups.length > 0 && (
        <ChildrenTabs
          dataAll={dataAll}
          isLoading={isLoading}
          applications={applications}
          wpmDatabases={wpmDatabases}
          wpmServers={wpmServers}
          moveGroups={moveGroups}
          schemas={schemas}
          selectedMoveGroups={selectedMoveGroups}
          onApplicationSelection={handleApplicationSelectToShowModal}
        />
      )}

      {/* Asset Transfer Modal */}
      <Modal
        visible={isAssetModalVisible}
        onDismiss={() => setIsAssetModalVisible(false)}
        size="max"
        header={<Header>Manage Assets in Move Groups</Header>}
      >
        {/* Force re-render each time model shows */}
        {isAssetModalVisible && selectedMoveGroup && (
          <TransferList
            header={
              <Header variant="h3" description="Transfer assets between move groups to organize your migration.">
                Manage Assets in Move Groups
              </Header>
            }
            parent={{
              records: [selectedMoveGroup],
              labelAttribute: "move_group_name",
              valueAttribute: "move_group_id",
              selectedValue: selectedMoveGroup.move_group_id,
            }}
            child={{
              records: allAssets,
              valueAttribute: "assetId",
              relationshipAttribute: "move_group_id",
              filteringAttributes: [
                "assetName",
                "assetType",
                "server_os_family",
                "server_tier",
                "database_type",
                "r_type",
              ],
              columnDefinitions: [
                {
                  id: "assetName",
                  header: "Asset Name",
                  cell: (item: Asset) => item.assetName,
                  sortingField: "assetName",
                },
                {
                  id: "assetType",
                  header: "Type",
                  cell: (item: Asset) => (item.assetType === "server" ? "Server" : "Database"),
                  sortingField: "assetType",
                },
                {
                  id: "details",
                  header: "Details",
                  cell: (item: Asset) => {
                    if (item.assetType === "server") {
                      return `${item.server_os_family || ""} | ${item.server_tier || ""}`;
                    } else {
                      return `${item.database_type || ""}`;
                    }
                  },
                },
                {
                  id: "r_type",
                  header: "Migration Strategy",
                  cell: (item: Asset) => item.r_type || "",
                  sortingField: "r_type",
                },
                {
                  id: "app_ids",
                  header: "Applications",
                  cell: (item: Asset) => item.app_ids.join(),
                  sortingField: "app_ids",
                },
              ],
            }}
            onCancel={() => setIsAssetModalVisible(false)}
            onConfirm={handleAssetTransferConfirm}
            customLabels={{
              sourceHeader: "Assets in Selected Move Group",
              sourceButtonText: "Remove from Move Group",
              targetHeader: "Available Assets",
              targetButtonText: "Add to Move Group",
            }}
          />
        )}
      </Modal>
      {/* Child app detail Modal */}
      <Modal
        header={selectedApplication?.app_name}
        onDismiss={() => setShowChildrenModal(false)}
        size={"max"}
        visible={showChildrenModal}
      >
        <ChildrenTabs
          dataAll={dataAll}
          isLoading={isLoading}
          applications={applications}
          wpmDatabases={wpmDatabases}
          wpmServers={wpmServers}
          moveGroups={moveGroups}
          schemas={schemas}
          selectedMoveGroups={selectedMoveGroups}
          selectedApplication={selectedApplication}
          hiddenTabs={[Schemas.Application.name, "entity_visualization"]}
        />
      </Modal>
    </SpaceBetween>
  );
};

/**
 * Props for the ChildrenTabs component that displays tabbed content for applications, servers, databases, and entity visualization.
 * @extends {Pick<MoveGroupStepProps, "applications" | "dataAll" | "isLoading" | "moveGroups" | "schemas" | "wpmDatabases" | "wpmServers">}
 */
interface ChildrenTabsProps extends Pick<
  MoveGroupStepProps,
  "applications" | "dataAll" | "isLoading" | "moveGroups" | "schemas" | "wpmDatabases" | "wpmServers"
> {
  /** Optional array of tab IDs to hide from display */
  readonly hiddenTabs?: string[];
  /** All data required for the ItemTable components to do relationship resolution and lookup */
  readonly dataAll: WPMAllData;
  /** Optional array of currently selected move groups in the parent ItemTable */
  readonly selectedMoveGroups?: MoveGroup[];
  /** Optional currently selected application */
  readonly selectedApplication?: Application;
  /**
   * If provided, the applications displayed in the ItemTable under Applications tab
   * will be selectable and this callback function will be called upon application
   * selection so that the parent component can display a Modal
   */
  readonly onApplicationSelection?: (app: Application) => void;
}

const ChildrenTabs = ({
  applications,
  dataAll,
  isLoading,
  moveGroups,
  schemas,
  wpmDatabases,
  wpmServers,
  selectedMoveGroups,
  selectedApplication,
  onApplicationSelection,
  hiddenTabs,
}: ChildrenTabsProps) => {
  // A filter function that filter assets by selectedMoveGroups and selectedApplication if provided (for modal use case)
  const visibleAssets = React.useCallback<<T extends Database | Server>(items: T[]) => T[]>(
    (assets) => {
      if (!assets?.length || !selectedMoveGroups?.length) {
        return [];
      }
      return assets.filter((asset) => {
        const appId = selectedApplication?.app_id;
        const inMg = selectedMoveGroups.some((mg) => asset.move_group_id === mg.move_group_id);
        const inApp = appId ? asset.app_ids?.includes(appId) : true;
        return inMg && inApp;
      });
    },
    [selectedApplication?.app_id, selectedMoveGroups]
  );

  // Filter visible servers based on selected move groups / app
  const visibleServers = React.useMemo(() => visibleAssets(wpmServers), [visibleAssets, wpmServers]);

  // Filter visible databases based on selected move groups / app
  const visibleDatabases = React.useMemo(() => visibleAssets(wpmDatabases), [visibleAssets, wpmDatabases]);

  // Filter visible apps based on selected move groups / app
  const visibleApplications = React.useMemo(() => {
    if (onApplicationSelection) {
      if (!selectedMoveGroups?.length) return [];
      // Get all app_ids from the selected move groups
      const selectedMoveGroupAppIds = selectedMoveGroups.flatMap((mg) => mg.app_ids || []);
      // Filter applications that are in the selected move groups
      return applications.filter((app: WPMApplication) => selectedMoveGroupAppIds.includes(app.app_id));
    } else {
      return selectedApplication ? [selectedApplication] : [];
    }
  }, [onApplicationSelection, selectedMoveGroups, applications, selectedApplication]);

  const [localSelectedApp, setLocalSelectedApp] = React.useState<Application>();

  const tabs: TabsProps["tabs"] = React.useMemo(
    () =>
      [
        {
          label: `${Schemas.Application.friendlyName}s`,
          id: Schemas.Application.name,
          content: (
            <ItemTable
              dataAll={dataAll}
              errorLoading={""}
              isLoading={isLoading}
              items={visibleApplications}
              schema={schemas[Schemas.Application.name]}
              schemaName={Schemas.Application.name}
              schemaKeyAttribute={Schemas.Application.keyAttribute}
              selectedItems={localSelectedApp ? [localSelectedApp] : []}
              selectionType={"single"}
              handleSelectionChange={(items: Application[]) => {
                setLocalSelectedApp(items[0]);
                onApplicationSelection?.(items[0]);
              }}
            />
          ),
        },
        {
          label: `${Schemas.Server.friendlyName}s`,
          id: Schemas.Server.name,
          content: (
            <ItemTable
              dataAll={dataAll}
              errorLoading={""}
              isLoading={isLoading}
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
              errorLoading={""}
              isLoading={isLoading}
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
                  moveGroups={moveGroups}
                  selectedMoveGroups={selectedMoveGroups}
                  applications={applications}
                  databases={wpmDatabases}
                  servers={wpmServers}
                />
              </div>
            </Container>
          ),
        },
      ].filter((t) => !hiddenTabs?.includes(t.id)),
    [
      applications,
      dataAll,
      hiddenTabs,
      isLoading,
      localSelectedApp,
      moveGroups,
      onApplicationSelection,
      schemas,
      selectedMoveGroups,
      visibleApplications,
      visibleDatabases,
      visibleServers,
      wpmDatabases,
      wpmServers,
    ]
  );

  return <Tabs tabs={tabs} />;
};

export default React.memo(MoveGroupStep) as typeof MoveGroupStep;
