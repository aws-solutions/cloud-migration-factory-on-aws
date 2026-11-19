/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import ItemAmend from "../components/ItemAmend";
import { getChanges } from "../resources/main";
import { exportTable } from "../utils/xlsx-export";
import { SpaceBetween } from "@cloudscape-design/components";

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
import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import { apiActionErrorHandler, parsePUTResponseErrors, UNEXPECTED_ERROR } from "../resources/recordFunctions";
import { Schemas } from "../utils/Constants";
import { ErrorWithType, useErrorHandler } from "../actions/ErrorHandlerHook";
import UserApiClient from "../api_clients/userApiClient";
import ToolsApiClient from "../api_clients/toolsApiClient";

import ServerView from "../components/ServerView";
import ItemTable from "../components/ItemTable";
import { NotificationContext } from "../contexts/NotificationContext";
import { ToolsContext } from "../contexts/ToolsContext";
import { CMFModal } from "../components/Modal";
import { useGetDatabases } from "../actions/DatabasesHook";
import { useGetItems } from "../actions/ItemsHook";

type DataAll = {
  readonly app: DataLoadingState<Application>;
  readonly database: DataLoadingState<Database>;
  readonly server: DataLoadingState<Server>;
  readonly move_group: DataLoadingState<MoveGroup>;
  readonly wave: DataLoadingState<Wave>;
  readonly wpm_job: DataLoadingState<WPMJob>;
};

type UserServerTableParams = {
  schemas: Record<string, EntitySchema>;
  userEntityAccess: UserAccess;
  schemaIsLoading?: boolean;
};

const schemaName = Schemas.Server.name;
const apiUser = new UserApiClient();
const apiTools = new ToolsApiClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const handlePutErrors = (result: any) => {
  if (result?.errors) {
    const errorsReturned = parsePUTResponseErrors(result.errors).join(",");
    throw new ErrorWithType(errorsReturned, "error");
  }
};

const UserServerTable = ({ schemas, userEntityAccess }: UserServerTableParams) => {
  const { addNotification } = React.useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = React.useContext(ToolsContext);
  const handleError = useErrorHandler();

  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  //Data items for viewer and table.
  const [appLoadingState, { update: updateApps }] = useMFApps<Application>();
  const [databaseLoadingState] = useGetDatabases<Database>();
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

  // Is in add/edit mode
  const editingItem = React.useRef(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = React.useState<Server[]>([]);
  const [focusItem, setFocusItem] = React.useState<Server>();
  const [viewCurrentTab, setViewCurrentTab] = React.useState("details");

  const entityLabel = React.useMemo(() => schemaName + (selectedItems.length > 1 ? "s" : ""), [selectedItems]);

  //Viewer pane state management.
  const [action, setAction] = React.useState<"Add" | "Edit">("Add");

  //Get base path from the URL, all actions will use this base path.
  const basePath = React.useMemo(
    () => (location.pathname.split("/").length >= 2 ? "/" + location.pathname.split("/")[1] : "/"),
    [location.pathname]
  );

  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState<boolean>(false);

  const handleAddItem = React.useCallback(() => {
    editingItem.current = true;
    navigate({
      pathname: basePath + "/add",
    });
    setAction("Add");
    setFocusItem(undefined);
  }, [basePath, navigate]);

  const handleDownloadItems = React.useCallback(() => {
    exportTable(selectedItems.length > 0 ? selectedItems : serverLoadingState.data, "Servers", "servers");
  }, [serverLoadingState.data, selectedItems]);

  const handleEditItem = React.useCallback(
    (selection: Server | null = null) => {
      editingItem.current = true;
      if (selectedItems.length === 1) {
        navigate({
          pathname: basePath + "/edit/" + selectedItems[0].server_id,
        });
        setAction("Edit");
        setFocusItem(selectedItems[0]);
      } else if (selection) {
        navigate({
          pathname: basePath + "/edit/" + selection.server_id,
        });
        setAction("Edit");
        setFocusItem(selection);
      }
    },
    [basePath, navigate, selectedItems]
  );

  const handleResetScreen = React.useCallback(() => {
    editingItem.current = false;
    navigate({
      pathname: basePath,
    });
  }, [basePath, navigate]);

  const handleItemSelectionChange = React.useCallback(
    (selection: Server[]) => {
      setSelectedItems(selection);
      //Reset URL to base table path.
      navigate({
        pathname: basePath,
      });
    },
    [basePath, navigate]
  );

  const getDataChanges = React.useCallback(
    (serverId: string, svr?: Server) => {
      // Find out the changed appIds
      const orig = serverLoadingState.data.find((x) => x.server_id === serverId);
      const origAppIdsSet = new Set((orig?.app_ids ?? []).filter((x): x is string => !!x));
      const updatedAppIdSet = new Set((svr?.app_ids ?? []).filter((x): x is string => !!x));
      const addedAppIds = Array.from(updatedAppIdSet).filter((x) => !origAppIdsSet.has(x));
      const removedAppIds = Array.from(origAppIdsSet).filter((item) => !updatedAppIdSet.has(item));

      return { orig, addedAppIds, removedAppIds };
    },
    [serverLoadingState.data]
  );

  // Callback function to update the delta of appIds
  const callApiToUpdateApps = React.useCallback(
    async (serverId: string, params: { addedAppIds: string[]; removedAppIds: string[] }) => {
      // Helper function to update an app's server_ids
      const updateApp = async (appId: string, isAdding: boolean) => {
        const app = appLoadingState.data.find((x) => x.app_id === appId);
        if (!app) throw new ErrorWithType(`App ${appId} not found`, "error");

        let serverIds: string[];
        if (isAdding) {
          if (app.server_ids?.includes(serverId)) return;
          serverIds = [...(app.server_ids ?? []), serverId];
        } else {
          if (!app.server_ids?.length || !app.server_ids.includes(serverId)) return;
          serverIds = app.server_ids.filter((x) => x !== serverId);
        }
        const result = await apiUser.putItem(appId, { server_ids: serverIds }, Schemas.Application.name);
        handlePutErrors(result);
      };

      // Update all affected apps
      await Promise.all([
        ...params.addedAppIds.map((appId) => updateApp(appId, true)),
        ...params.removedAppIds.map((appId) => updateApp(appId, false)),
      ]);
    },
    [appLoadingState.data]
  );

  const callApisToSave = React.useCallback(
    async (db: Server) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let result: any;
      let saved: Server;
      // Create/update server
      if (!db.server_id) {
        result = await apiUser.postItem(db, Schemas.Server.name);
        saved = result.newItems[0];
      } else {
        const changes = getChanges(db, serverLoadingState.data, Schemas.Server.keyAttribute);
        if (!changes) throw new ErrorWithType("No updates to save.", "warning");

        result = await apiUser.putItem(db.server_id, changes, Schemas.Server.name);
        saved = db;
      }
      handlePutErrors(result);

      const { orig, addedAppIds, removedAppIds } = getDataChanges(saved.server_id, saved);

      // Update apps if there are added appIds or removed appIds
      if (addedAppIds.length > 0 || removedAppIds.length > 0) {
        await callApiToUpdateApps(saved.server_id, { addedAppIds, removedAppIds });
      }
      // Update move group if appIds changed and there is/was move group assigned, or move group indeed changed
      if (
        ((addedAppIds.length > 0 || removedAppIds.length > 0) && (saved.move_group_id || orig?.move_group_id)) ||
        saved.move_group_id !== orig?.move_group_id
      ) {
        await apiTools.manageEntities({
          operation: OperationType.MOVE,
          source_entity_type: "move_group",
          source_entity_id: orig?.move_group_id,
          destination_entity_type: "move_group",
          destination_entity_id: db?.move_group_id,
          target_entities: [
            {
              entity_id: saved.server_id,
              entity_type: "server",
            },
          ],
        });
      }
    },
    [callApiToUpdateApps, getDataChanges, serverLoadingState.data]
  );

  const handleRefreshClick = React.useCallback(() => {
    refreshServers();
    refreshApps();
    refreshMoveGroups();
    refreshWaves();
  }, [refreshApps, refreshMoveGroups, refreshServers, refreshWaves]);

  const handleSave = React.useCallback(
    async (editItem: Server, action: string) => {
      const header = `${action} ${Schemas.Server.name}`;

      const item = Object.assign({}, editItem);
      try {
        if (action === "Edit") {
          await callApisToSave(item);
          addNotification({
            type: "success",
            dismissible: true,
            header,
            content: item.server_name + " updated successfully.",
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
            content: item.server_name + " added successfully.",
          });
        }
        handleRefreshClick();
        handleResetScreen();
      } catch (e) {
        if (e instanceof ErrorWithType) handleError(e, { header });
        else apiActionErrorHandler(action, Schemas.Server.name, e, addNotification);
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
        "server",
        selectedItems.map((item) => item.server_id)
      );

      //Create notification where multi select was used.
      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: `Delete ${entityLabel}`,
        content: `${selectedItems.map((item) => item.server_name).join(", ")} ${selectedItems.length > 1 ? "were" : "was"} deleted.`,
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

  // Make cascade changes: wave_id based on move_group_id
  const handleItemUpdate = React.useCallback(
    (item: Server) => {
      const mgId = item.move_group_id;
      const wave = mgId ? waveLoadingState.data.find((w) => w.move_group_ids?.includes(mgId)) : undefined;
      const delta: Partial<Server> = {};
      delta.wave_id = wave?.wave_id;
      setFocusItem({ ...item, ...delta });
    },
    [waveLoadingState.data]
  );

  function displayItemsViewScreen() {
    return (
      <SpaceBetween direction="vertical" size="xs">
        <ItemTable
          schema={schemas[schemaName]}
          schemaKeyAttribute={Schemas.Server.keyAttribute}
          schemaName={schemaName}
          dataAll={dataAll}
          items={serverLoadingState.data}
          selectedItems={selectedItems}
          handleSelectionChange={handleItemSelectionChange}
          isLoading={serverLoadingState.isLoading || isDeleting}
          errorLoading={serverLoadingState.error}
          handleRefreshClick={handleRefreshClick}
          handleAddItem={handleAddItem}
          handleDeleteItem={() => setDeleteConfirmationModalVisible(true)}
          handleEditItem={handleEditItem}
          handleDownloadItems={handleDownloadItems}
          userAccess={userEntityAccess}
        />
        {selectedItems.length === 1 ? (
          <ServerView
            schemas={schemas}
            server={selectedItems[0]}
            dataAll={dataAll}
            selectedTab={viewCurrentTab}
            handleTabChange={setViewCurrentTab}
          />
        ) : undefined}
      </SpaceBetween>
    );
  }

  function displayItemsScreen() {
    if (editingItem.current) {
      return (
        <ItemAmend
          action={action}
          schemaName={schemaName}
          schemas={schemas}
          userAccess={userEntityAccess}
          item={focusItem}
          handleItemUpdate={handleItemUpdate}
          handleSave={handleSave}
          handleCancel={handleResetScreen}
        />
      );
    } else {
      return displayItemsViewScreen();
    }
  }

  React.useEffect(() => {
    if (!serverLoadingState.isLoading) {
      const item = serverLoadingState.data.find((entry) => {
        return entry.server_id === params.id;
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
    params.id,
    selectedItems.length,
    serverLoadingState.data,
    serverLoadingState.isLoading,
  ]);

  //Update help tools panel
  React.useEffect(() => {
    setHelpPanelContentFromSchema(schemas, schemaName);
  }, [schemas, setHelpPanelContentFromSchema]);

  return (
    <div>
      {displayItemsScreen()}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={"Delete servers"}
      >
        <p>Are you sure you wish to delete the {selectedItems.length} selected servers?</p>
      </CMFModal>
    </div>
  );
};
export default UserServerTable;
