/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { SpaceBetween } from "@cloudscape-design/components";

import ItemAmend from "../components/ItemAmend";
import ItemTable from "../components/ItemTable";
import { CMFModal } from "../components/Modal";
import { MoveGroupDetailsView } from "../components/MoveGroupView";
import { NotificationContext } from "../contexts/NotificationContext";
import { ToolsContext } from "../contexts/ToolsContext";

import { useMFApps } from "../actions/ApplicationsHook";
import { useGetItems } from "../actions/ItemsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import {
  Application,
  Database,
  DataLoadingState,
  EntitySchema,
  MoveGroup,
  OperationType,
  Server,
  UserAccess,
  Wave,
  WPMJob,
} from "../models";
import { getChanges } from "../resources/main";
import { apiActionErrorHandler, parsePUTResponseErrors, UNEXPECTED_ERROR } from "../resources/recordFunctions";
import { Schemas } from "../utils/Constants";
import { exportTable } from "../utils/xlsx-export";
import ToolsApiClient from "../api_clients/toolsApiClient";
import UserApiClient from "../api_clients/userApiClient";
import { useGetDatabases } from "../actions/DatabasesHook";
import { ErrorWithType, useErrorHandler } from "../actions/ErrorHandlerHook";

type UserMoveGroupTableParams = {
  userEntityAccess: UserAccess;
  schemas: Record<string, EntitySchema>;
};

type DataAll = {
  readonly app: DataLoadingState<Application>;
  readonly database: DataLoadingState<Database>;
  readonly server: DataLoadingState<Server>;
  readonly move_group: DataLoadingState<MoveGroup>;
  readonly wave: DataLoadingState<Wave>;
  readonly wpm_job: DataLoadingState<WPMJob>;
};

const schemaName = Schemas.MoveGroup.name;
const apiUser = new UserApiClient();
const apiTools = new ToolsApiClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const handlePutErrors = (result: any) => {
  if (result?.errors) {
    const errorsReturned = parsePUTResponseErrors(result.errors).join(",");
    throw new ErrorWithType(errorsReturned, "error");
  }
};

const UserMoveGroupsTable = ({ schemas, userEntityAccess }: UserMoveGroupTableParams) => {
  const { addNotification } = React.useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = React.useContext(ToolsContext);
  const handleError = useErrorHandler();

  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  //Data items for viewer and table.
  const [appLoadingState, { update: updateApps }] = useMFApps<Application>();
  const [databaseLoadingState, { update: refreshDatabases }] = useGetDatabases<Database>();
  const [serverLoadingState, { update: refreshServers }] = useGetServers<Server>();
  const [moveGroupLoadingState, { update: updateMoveGroups }] = useGetItems<MoveGroup>(Schemas.MoveGroup.name);
  const [waveLoadingState, { update: updateWaves }] = useMFWaves<Wave>();
  const [wpmJobLoadingState] = useGetItems<WPMJob>(Schemas.WPMJob.name);

  const refreshApps = React.useCallback(() => updateApps(Schemas.Application.name), [updateApps]);
  const refreshMoveGroups = React.useCallback(() => updateMoveGroups(Schemas.MoveGroup.name), [updateMoveGroups]);
  const refreshWaves = React.useCallback(() => updateWaves(Schemas.Wave.name), [updateWaves]);

  const dataAll: DataAll = React.useMemo(
    () => ({
      app: appLoadingState,
      database: databaseLoadingState,
      server: serverLoadingState,
      move_group: moveGroupLoadingState,
      wave: waveLoadingState,
      wpm_job: wpmJobLoadingState,
    }),
    [
      appLoadingState,
      databaseLoadingState,
      moveGroupLoadingState,
      serverLoadingState,
      waveLoadingState,
      wpmJobLoadingState,
    ]
  );

  //Main table state management.
  const [selectedItems, setSelectedItems] = React.useState<MoveGroup[]>([]);
  const [focusItem, setFocusItem] = React.useState<MoveGroup>();

  //Viewer pane state management.
  const [action, setAction] = React.useState<"Add" | "Edit" | "View">("View");
  const [viewCurrentTab, setViewCurrentTab] = React.useState("details");

  const entityLabel = React.useMemo(() => schemaName + (selectedItems.length > 1 ? "s" : ""), [selectedItems]);

  //Get base path from the URL, all actions will use this base path.
  const basePath = React.useMemo(
    () => (location.pathname.split("/").length >= 2 ? "/" + location.pathname.split("/")[1] : "/"),
    [location.pathname]
  );

  //Modals
  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState<boolean>(false);

  // Refresh all entities that might be affected by change (e.g. move group between waves)
  const handleRefreshClick = React.useCallback(() => {
    refreshMoveGroups();
    refreshDatabases();
    refreshServers();
    refreshApps();
    refreshWaves();
  }, [refreshApps, refreshDatabases, refreshMoveGroups, refreshServers, refreshWaves]);

  const handleAddItem = React.useCallback(() => {
    navigate({
      pathname: basePath + "/add",
    });
    setAction("Add");
    setFocusItem(undefined);
  }, [basePath, navigate]);

  const handleDownloadItems = React.useCallback(() => {
    exportTable(selectedItems.length > 0 ? selectedItems : moveGroupLoadingState.data, "Move Groups", "move_groups");
  }, [moveGroupLoadingState.data, selectedItems]);

  const handleEditItem = React.useCallback(
    (selection: MoveGroup | null = null) => {
      if (selectedItems.length === 1) {
        navigate({
          pathname: basePath + "/edit/" + selectedItems[0].move_group_id,
        });
        setAction("Edit");
        setFocusItem(selectedItems[0]);
      } else if (selection) {
        navigate({
          pathname: basePath + "/edit/" + selection.move_group_id,
        });
        setAction("Edit");
        setFocusItem(selection);
      }
    },
    [basePath, navigate, selectedItems]
  );

  const handleResetScreen = React.useCallback(() => {
    setAction("View");
    navigate({
      pathname: basePath,
    });
  }, [basePath, navigate]);

  const handleItemSelectionChange = React.useCallback(
    (selection: MoveGroup[]) => {
      setSelectedItems(selection);
      //Reset URL to base table path.
      navigate({
        pathname: basePath,
      });
    },
    [basePath, navigate]
  );

  const callApisToSave = React.useCallback(
    async (mg: MoveGroup) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let result: any;
      let saved: MoveGroup;
      // Create/update move group
      if (!mg.move_group_id) {
        result = await apiUser.postItem(mg, Schemas.MoveGroup.name);
        saved = result.newItems[0];
      } else {
        const changes = getChanges(mg, moveGroupLoadingState.data, Schemas.MoveGroup.keyAttribute);
        if (!changes) throw new ErrorWithType("No updates to save.", "warning");

        result = await apiUser.putItem(mg.move_group_id, changes, Schemas.MoveGroup.name);
        saved = mg;
      }
      handlePutErrors(result);

      const orig = moveGroupLoadingState.data.find((x) => x.move_group_id === saved.move_group_id);

      // Call manage-entities API if wave_id change
      if (saved.wave_id !== orig?.wave_id) {
        await apiTools.manageEntities({
          operation: OperationType.MOVE,
          source_entity_type: "wave",
          source_entity_id: orig?.wave_id,
          destination_entity_type: "wave",
          destination_entity_id: saved.wave_id,
          target_entities: [
            {
              entity_id: saved.move_group_id,
              entity_type: "move_group",
            },
          ],
        });
      }
    },
    [moveGroupLoadingState.data]
  );

  const handleSave = React.useCallback(
    async (editItem: MoveGroup, action: string) => {
      const header = `${action} ${Schemas.MoveGroup.name}`;

      const item = Object.assign({}, editItem);
      try {
        if (action === "Edit") {
          await callApisToSave(item);
          addNotification({
            type: "success",
            dismissible: true,
            header,
            content: item.move_group_name + " updated successfully.",
          });

          //This is needed to ensure the item in selectItems reflects new updates
          setSelectedItems([]);
          setFocusItem(undefined);
        } else {
          await callApisToSave(item);
          addNotification({
            type: "success",
            dismissible: true,
            header,
            content: item.move_group_name + " added successfully.",
          });
        }
        handleRefreshClick();
        handleResetScreen();
      } catch (e) {
        if (e instanceof ErrorWithType) handleError(e, { header });
        else apiActionErrorHandler(action, Schemas.MoveGroup.name, e, addNotification);
      }
    },
    [handleRefreshClick, handleResetScreen, callApisToSave, addNotification, handleError]
  );

  const handleDeleteItem = React.useCallback(async () => {
    setDeleteConfirmationModalVisible(false);

    let notificationId;

    const currentSelectedItems = selectedItems;
    setIsDeleting(true);
    // Clear selected items so as to disable Edit/Edit buttons during deletion
    setSelectedItems([]);

    try {
      notificationId = addNotification({
        loading: true,
        dismissible: false,
        header: `Deleting selected ${entityLabel}...`,
      });

      await apiTools.cleanupEntities(
        "move_group",
        selectedItems.map((item) => item.move_group_id)
      );

      //Create notification where multi select was used.
      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: `Delete ${entityLabel}`,
        content: `${selectedItems.map((item) => item.move_group_name).join(", ")} ${selectedItems.length > 1 ? "were" : "was"} deleted.`,
      });

      handleRefreshClick();
    } catch (e) {
      console.error(e);
      // Revert selected items on error
      setSelectedItems(currentSelectedItems);
      addNotification({
        id: notificationId,
        type: "error",
        dismissible: true,
        header: `Delete ${entityLabel}`,
        content: UNEXPECTED_ERROR,
      });
    } finally {
      setIsDeleting(false);
    }
  }, [selectedItems, addNotification, entityLabel, handleRefreshClick]);

  //Update help tools panel.
  React.useEffect(() => {
    setHelpPanelContentFromSchema(schemas, schemaName);
  }, [schemas, setHelpPanelContentFromSchema]);

  function provideContent(currentAction: string) {
    switch (currentAction) {
      case "Add":
      case "Edit":
        return (
          <ItemAmend
            action={action}
            schemaName={schemaName}
            schemas={schemas}
            userAccess={userEntityAccess}
            item={focusItem}
            handleSave={handleSave}
            handleCancel={handleResetScreen}
          />
        );
      default:
        return (
          <SpaceBetween direction="vertical" size="xs">
            <ItemTable
              schema={schemas[schemaName]}
              schemaKeyAttribute={Schemas.MoveGroup.keyAttribute}
              schemaName={schemaName}
              dataAll={dataAll}
              items={moveGroupLoadingState.data}
              selectedItems={selectedItems}
              handleSelectionChange={handleItemSelectionChange}
              isLoading={moveGroupLoadingState.isLoading || isDeleting}
              errorLoading={moveGroupLoadingState.error}
              handleRefreshClick={handleRefreshClick}
              handleAddItem={handleAddItem}
              handleDeleteItem={() => setDeleteConfirmationModalVisible(true)}
              handleEditItem={handleEditItem}
              handleDownloadItems={handleDownloadItems}
              userAccess={userEntityAccess}
            />
            <MoveGroupDetailsView
              schemas={schemas}
              selectedItems={selectedItems}
              dataAll={dataAll}
              selectedTab={viewCurrentTab}
              handleTabChange={setViewCurrentTab}
            />
          </SpaceBetween>
        );
    }
  }

  React.useEffect(() => {
    if (!moveGroupLoadingState.isLoading) {
      const item = moveGroupLoadingState.data.find((entry) => {
        return entry.move_group_id === params.id;
      });

      if (item) {
        if (selectedItems.length === 0) {
          setSelectedItems([item]);
        }
        //Check if URL contains edit path and switch to amend component.
        if (location?.pathname.match("/edit/")) {
          handleEditItem(item);
        }
      } else if (location?.pathname.match("/add")) {
        //Add url used, redirect to add screen.
        handleAddItem();
      }
    }
  }, [
    handleAddItem,
    handleEditItem,
    location?.pathname,
    moveGroupLoadingState.data,
    moveGroupLoadingState.isLoading,
    params.id,
    selectedItems.length,
  ]);

  return (
    <div>
      {provideContent(action)}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={"Delete move groups"}
      >
        <p>Are you sure you wish to delete the {selectedItems.length} selected move groups?</p>
      </CMFModal>
    </div>
  );
};
export default UserMoveGroupsTable;
