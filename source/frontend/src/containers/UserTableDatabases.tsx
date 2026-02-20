/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { SpaceBetween } from "@cloudscape-design/components";

import ItemAmend from "../components/ItemAmend";
import { getChanges } from "../resources/main";
import { exportTable } from "../utils/xlsx-export";

import DatabaseView from "../components/DatabaseView";
import { useMFApps } from "../actions/ApplicationsHook";
import { useGetDatabases } from "../actions/DatabasesHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import ItemTable from "../components/ItemTable";
import { apiActionErrorHandler, parsePUTResponseErrors, UNEXPECTED_ERROR } from "../resources/recordFunctions";
import { NotificationContext } from "../contexts/NotificationContext";
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
import { ToolsContext } from "../contexts/ToolsContext";
import { CMFModal } from "../components/Modal";
import { Schemas } from "../utils/Constants";
import { useGetItems } from "../actions/ItemsHook";
import { ErrorWithType, useErrorHandler } from "../actions/ErrorHandlerHook";
import ToolsApiClient from "../api_clients/toolsApiClient";
import UserApiClient from "../api_clients/userApiClient";

type DataAll = {
  readonly app: DataLoadingState<Application>;
  readonly database: DataLoadingState<Database>;
  readonly server: DataLoadingState<Server>;
  readonly move_group: DataLoadingState<MoveGroup>;
  readonly wave: DataLoadingState<Wave>;
  readonly wpm_job: DataLoadingState<WPMJob>;
};

const ViewItem = (props: { schema: Record<string, EntitySchema>; selectedItems: Database[]; dataAll: DataAll }) => {
  const [viewerCurrentTab, setViewerCurrentTab] = React.useState("details");

  if (props.selectedItems.length === 1) {
    return (
      <DatabaseView
        schema={props.schema}
        database={props.selectedItems[0]}
        handleTabChange={setViewerCurrentTab}
        dataAll={props.dataAll}
        selectedTab={viewerCurrentTab}
      />
    );
  } else {
    return null;
  }
};

type UserDatabaseTableParams = {
  schemas: Record<string, EntitySchema>;
  userEntityAccess: UserAccess;
  schemaIsLoading?: boolean;
};

const apiUser = new UserApiClient();
const apiTools = new ToolsApiClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const handlePutErrors = (result: any) => {
  if (result?.errors) {
    const errorsReturned = parsePUTResponseErrors(result.errors).join(",");
    throw new ErrorWithType(errorsReturned, "error");
  }
};

const UserDatabaseTable = (props: UserDatabaseTableParams) => {
  const { addNotification } = React.useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = React.useContext(ToolsContext);
  const handleError = useErrorHandler();

  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  const schema = React.useMemo(() => props.schemas[Schemas.Database.name], [props.schemas]);
  //Data items for viewer and table.
  const [appLoadingState, { update: updateApps }] = useMFApps<Application>();
  const [databaseLoadingState, { update: refreshDatabases }] = useGetDatabases<Database>();
  const [serverLoadingState] = useGetServers<Server>();
  const [moveGroupLoadingState, { update: updateMoveGroups }] = useGetItems<MoveGroup>(Schemas.MoveGroup.name);
  const [waveLoadingState] = useMFWaves<Wave>();
  const [wpmJobLoadingState] = useGetItems<WPMJob>(Schemas.WPMJob.name);

  const refreshApps = React.useCallback(() => updateApps(Schemas.Application.name), [updateApps]);
  const refreshMoveGroups = React.useCallback(() => updateMoveGroups(Schemas.MoveGroup.name), [updateMoveGroups]);

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
  const [selectedItems, setSelectedItems] = React.useState<Database[]>([]);
  const [focusItem, setFocusItem] = React.useState<Database>();

  const headerEntity = React.useMemo(
    () => Schemas.Database.name + (selectedItems.length > 1 ? "s" : ""),
    [selectedItems]
  );

  //Viewer pane state management.
  const [action, setAction] = React.useState("Add");

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
    exportTable(
      selectedItems.length ? selectedItems : serverLoadingState.data,
      `${Schemas.Database.friendlyName}s`,
      `${Schemas.Database.name}s`
    );
  }, [selectedItems, serverLoadingState.data]);

  const handleEditItem = React.useCallback(
    (selection: Database | null = null) => {
      editingItem.current = true;
      if (selectedItems.length === 1) {
        navigate({
          pathname: basePath + "/edit/" + selectedItems[0].database_id,
        });
        setAction("Edit");
        setFocusItem(selectedItems[0]);
      } else if (selection) {
        navigate({
          pathname: basePath + "/edit/" + selection.database_id,
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
    (selection: Database[]) => {
      setSelectedItems(selection);
      //Reset URL to base table path.
      navigate({
        pathname: basePath,
      });
    },
    [basePath, navigate]
  );

  const getDataChanges = React.useCallback(
    (databaseId: string, db?: Database) => {
      // Find out the changed appIds
      const orig = databaseLoadingState.data.find((x) => x.database_id === databaseId);
      const origAppIdsSet = new Set((orig?.app_ids ?? []).filter((x): x is string => !!x));
      const updatedAppIdSet = new Set((db?.app_ids ?? []).filter((x): x is string => !!x));
      const addedAppIds = Array.from(updatedAppIdSet).filter((x) => !origAppIdsSet.has(x));
      const removedAppIds = Array.from(origAppIdsSet).filter((item) => !updatedAppIdSet.has(item));

      return { orig, addedAppIds, removedAppIds };
    },
    [databaseLoadingState.data]
  );

  // Callback function to update the delta of appIds
  const callApiToUpdateApps = React.useCallback(
    async (databaseId: string, params: { addedAppIds: string[]; removedAppIds: string[] }) => {
      // Helper function to update an app's database_ids
      const updateApp = async (appId: string, isAdding: boolean) => {
        const app = appLoadingState.data.find((x) => x.app_id === appId);
        if (!app) throw new ErrorWithType(`App ${appId} not found`, "error");

        let databaseIds: string[];
        if (isAdding) {
          if (app.database_ids?.includes(databaseId)) return;
          databaseIds = [...(app.database_ids ?? []), databaseId];
        } else {
          if (!app.database_ids?.length || !app.database_ids.includes(databaseId)) return;
          databaseIds = app.database_ids.filter((x) => x !== databaseId);
        }
        const result = await apiUser.putItem(appId, { database_ids: databaseIds }, Schemas.Application.name);
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
    async (db: Database) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let result: any;
      let saved: Database;
      // Create/update database
      if (!db.database_id) {
        result = await apiUser.postItem(db, Schemas.Database.name);
        saved = result.newItems[0];
      } else {
        const changes = getChanges(db, databaseLoadingState.data, Schemas.Database.keyAttribute);
        if (!changes) throw new ErrorWithType("No updates to save.", "warning");

        result = await apiUser.putItem(db.database_id, changes, Schemas.Database.name);
        saved = db;
      }
      handlePutErrors(result);

      const { orig, addedAppIds, removedAppIds } = getDataChanges(saved.database_id, saved);

      // Update apps if there are added appIds or removed appIds
      if (addedAppIds.length > 0 || removedAppIds.length > 0) {
        await callApiToUpdateApps(saved.database_id, { addedAppIds, removedAppIds });
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
              entity_id: saved.database_id,
              entity_type: "database",
            },
          ],
        });
      }
    },
    [callApiToUpdateApps, databaseLoadingState.data, getDataChanges]
  );

  const handleRefreshClick = React.useCallback(() => {
    refreshDatabases();
    refreshApps();
    refreshMoveGroups();
  }, [refreshApps, refreshDatabases, refreshMoveGroups]);

  const handleSave = React.useCallback(
    async (editItem: Database, action: string) => {
      const header = `${action} ${Schemas.Database.name}`;

      const item = Object.assign({}, editItem);
      try {
        if (action === "Edit") {
          await callApisToSave(item);
          addNotification({
            type: "success",
            dismissible: true,
            header,
            content: item.database_name + " updated successfully.",
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
            content: item.database_name + " added successfully.",
          });
        }
        handleRefreshClick();
        handleResetScreen();
      } catch (e) {
        if (e instanceof ErrorWithType) handleError(e, { header });
        else apiActionErrorHandler(action, Schemas.Database.name, e, addNotification);
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
        header: `Deleting selected ${headerEntity}...`,
      });

      await apiTools.cleanupEntities(
        "database",
        selectedItems.map((item) => item.database_id)
      );

      //Create notification where multi select was used.
      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: `Delete ${headerEntity}`,
        content: `${selectedItems.map((item) => item.database_name).join(", ")} ${selectedItems.length > 1 ? "were" : "was"} deleted.`,
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
        header: `Delete ${headerEntity}`,
        content: UNEXPECTED_ERROR,
      });
    } finally {
      setIsDeleting(false);
    }
  }, [selectedItems, addNotification, headerEntity, handleRefreshClick]);

  // Make cascade changes: wave_id based on move_group_id
  const handleItemUpdate = React.useCallback(
    (item: Database) => {
      const mgId = item.move_group_id;
      const wave = mgId ? waveLoadingState.data.find((w) => w.move_group_ids?.includes(mgId)) : undefined;
      const delta: Partial<Database> = {};
      delta.wave_id = wave?.wave_id;
      setFocusItem({ ...item, ...delta });
    },
    [waveLoadingState.data]
  );

  function displayItemsViewScreen() {
    return (
      <SpaceBetween direction="vertical" size="xs">
        <ItemTable
          schema={schema}
          schemaKeyAttribute={Schemas.Database.keyAttribute}
          schemaName={Schemas.Database.name}
          dataAll={dataAll}
          items={databaseLoadingState.data}
          selectedItems={selectedItems}
          handleSelectionChange={handleItemSelectionChange}
          isLoading={databaseLoadingState.isLoading || isDeleting}
          errorLoading={databaseLoadingState.error}
          handleRefreshClick={handleRefreshClick}
          handleAddItem={handleAddItem}
          handleDeleteItem={async function () {
            setDeleteConfirmationModalVisible(true);
          }}
          handleEditItem={handleEditItem}
          handleDownloadItems={handleDownloadItems}
          userAccess={props.userEntityAccess}
        />
        <ViewItem schema={props.schemas} selectedItems={selectedItems} dataAll={dataAll} />
      </SpaceBetween>
    );
  }

  function displayItemsScreen() {
    if (editingItem.current) {
      return (
        <ItemAmend
          action={action}
          schemaName={Schemas.Database.name}
          schemas={props.schemas}
          userAccess={props.userEntityAccess}
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
    if (!databaseLoadingState.isLoading) {
      const item = databaseLoadingState.data.find((entry) => {
        return entry.database_id === params.id;
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
    databaseLoadingState.data,
    databaseLoadingState.isLoading,
    handleAddItem,
    handleEditItem,
    handleItemSelectionChange,
    location?.pathname,
    params.id,
    selectedItems.length,
  ]);

  //Update help tools panel.
  React.useEffect(() => {
    setHelpPanelContentFromSchema(props.schemas, Schemas.Database.name);
  }, [props.schemas, setHelpPanelContentFromSchema]);

  return (
    <div>
      {displayItemsScreen()}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={"Delete databases"}
      >
        <p>
          Are you sure you wish to delete the {selectedItems.length} selected {headerEntity}?
        </p>
      </CMFModal>
    </div>
  );
};

// Component TableView is a skeleton of a Table using AWS-UI React components.
export default UserDatabaseTable;
