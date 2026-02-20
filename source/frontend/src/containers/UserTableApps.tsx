/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { Alert, Box, Button, Modal, Pagination, SpaceBetween, Table, TableProps } from "@cloudscape-design/components";

import ApplicationView, { ApplicationViewDataAll } from "../components/ApplicationView";
import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import ItemAmend from "../components/ItemAmend";
import ItemTable from "../components/ItemTable";
import { capitalize, getChanges, getNestedValue, resolveRelationshipValues } from "../resources/main";
import { apiActionErrorHandler, parsePUTResponseErrors, UNEXPECTED_ERROR } from "../resources/recordFunctions";
import { NotificationContext } from "../contexts/NotificationContext";
import { ToolsContext } from "../contexts/ToolsContext";
import {
  DataLoadingState,
  EntitySchema,
  Application,
  Server,
  UserAccess,
  Wave,
  WPMJob,
  Database,
  MoveGroup,
} from "../models";
import { Schemas } from "../utils/Constants";
import { useGetItems } from "../actions/ItemsHook";
import { useGetDatabases } from "../actions/DatabasesHook";
import { exportTable } from "../utils/xlsx-export";
import UserApiClient from "../api_clients/userApiClient";
import ToolsApiClient from "../api_clients/toolsApiClient";
import { useCustomAssetItems } from "../actions/CustomAssetItemsHook";
import { useCollection } from "@cloudscape-design/collection-hooks";

type DataAll = ApplicationViewDataAll & {
  wpm_job: DataLoadingState<WPMJob>;
};

type AppTableParams = {
  readonly schemas: Record<string, EntitySchema>;
  readonly userEntityAccess: UserAccess;
  readonly schemaIsLoading?: boolean;
};

type EntityWithResolvedMoveGroup = Readonly<{
  __move_group_id?: string;
}>;

type AssetsWithMoveGroup = Readonly<{
  appName: string;
  entity: string;
  entityName: string;
  moveGroupName: string;
}>;

type AssetsCascadeDelete = Readonly<{
  entity: string;
  entityName: string;
  appNames: string;
}>;

type EmbeddedTableWithPaginationProps<T> = Pick<TableProps<T>, "items" | "sortingDisabled" | "columnDefinitions">;

// Table component embedded in Alert or Confirm modal with hardcoded pagination
const EmbeddedTableWithPagination = <T,>(props: EmbeddedTableWithPaginationProps<T>) => {
  const paginationOptions = React.useMemo(() => ({ pagination: { pageSize: 10 } }), []);
  const { items, paginationProps } = useCollection(props.items, paginationOptions);
  return <Table {...props} items={items} variant="embedded" pagination={<Pagination {...paginationProps} />} />;
};

const DeletionAlert = (props: {
  entityName: string;
  assetsWithMoveGroup: AssetsWithMoveGroup[];
  onDismiss: () => void;
}) => {
  if (props.assetsWithMoveGroup.length === 0) return null;

  return (
    <Alert
      type="warning"
      dismissible
      onDismiss={props.onDismiss}
      header={
        <SpaceBetween size="xxs">
          <Box variant="h5" display="inline">
            {capitalize(props.entityName)} cannot be deleted
          </Box>
          <Box display="inline">
            The following assets associated with some of the selected {props.entityName} have move group assigned.
            Please edit the assets to remove them from the groups first.
          </Box>
        </SpaceBetween>
      }
    >
      <EmbeddedTableWithPagination
        items={props.assetsWithMoveGroup}
        sortingDisabled
        columnDefinitions={[
          {
            header: "Application Name",
            cell: (item) => item.appName,
          },
          {
            header: "Entity Type",
            cell: (item) => item.entity,
          },
          {
            header: "Entity Name",
            cell: (item) => item.entityName,
          },
          {
            header: "Move Group Name",
            cell: (item) => item.moveGroupName,
          },
        ]}
      />
    </Alert>
  );
};

//Key for main item displayed in table.
const schemaName = Schemas.Application.name;

const apiUser = new UserApiClient();
const apiTools = new ToolsApiClient();

const AppTable = ({ schemas, userEntityAccess }: AppTableParams) => {
  const { addNotification } = React.useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = React.useContext(ToolsContext);

  const location = useLocation();
  const navigate = useNavigate();
  const urlParams = useParams();
  //Data items for viewer and table.
  //Main table content hook. When duplicating just create a new hook and change the hook function at the end to populate table.
  const [appLoadingState, { update: updateApps }] = useMFApps<Application>();
  const [databaseLoadingState, { update: refreshDatabases }] = useGetDatabases<Database>();
  const [serverLoadingState, { update: refreshServers }] = useGetServers<Server>();
  const [moveGroupLoadingState, { update: updateMoveGroups }] = useGetItems<MoveGroup>(Schemas.MoveGroup.name);
  const [waveLoadingState, { update: updateWaves }] = useMFWaves<Wave>();
  const [wpmJobLoadingState] = useGetItems<WPMJob>(Schemas.WPMJob.name);

  // Custom assets
  const [customAssetLoadingStates, refreshCustomAssets] = useCustomAssetItems(schemas);

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
      ...customAssetLoadingStates,
    }),
    [
      appLoadingState,
      databaseLoadingState,
      moveGroupLoadingState,
      serverLoadingState,
      waveLoadingState,
      wpmJobLoadingState,
      customAssetLoadingStates,
    ]
  );

  // Resolve relationships to get move group names for deletion check
  React.useEffect(() => {
    resolveRelationshipValues(dataAll, databaseLoadingState.data, schemas.database);
  }, [dataAll, databaseLoadingState.data, schemas.database]);

  React.useEffect(() => {
    resolveRelationshipValues(dataAll, serverLoadingState.data, schemas.server);
  }, [dataAll, schemas.server, serverLoadingState.data]);

  // Is in add/edit mode
  const editingItem = React.useRef(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = React.useState<Application[]>([]);
  const [focusItem, setFocusItem] = React.useState<Application>();
  const [viewCurrentTab, setViewCurrentTab] = React.useState("details");

  const entityNameInMessage = React.useMemo(
    () => Schemas.Application.name + (selectedItems.length > 1 ? "s" : ""),
    [selectedItems]
  );

  //Viewer pane state management.

  const [action, setAction] = React.useState("Add");

  //Get base path from the URL, all actions will use this base path.
  const basePath = React.useMemo(
    () => (location.pathname.split("/").length >= 2 ? "/" + location.pathname.split("/")[1] : "/"),
    [location.pathname]
  );

  //Modals
  const [modalVisible, setModalVisible] = React.useState(false);

  const handleRefreshClick = React.useCallback(() => {
    refreshApps();
    refreshDatabases();
    refreshServers();
    refreshMoveGroups();
    refreshWaves();
    refreshCustomAssets();
  }, [refreshApps, refreshDatabases, refreshMoveGroups, refreshServers, refreshWaves, refreshCustomAssets]);

  const handleAddItem = React.useCallback(() => {
    editingItem.current = true;
    navigate({
      pathname: basePath + "/add",
    });
    setAction("Add");
    setFocusItem(undefined);
  }, [basePath, navigate]);

  const handleDownloadItems = React.useCallback(() => {
    exportTable(selectedItems.length > 0 ? selectedItems : appLoadingState.data, "Applications", "applications");
  }, [appLoadingState.data, selectedItems]);

  const handleEditItem = React.useCallback(
    (selection: Application | null = null) => {
      editingItem.current = true;
      if (selectedItems.length === 1) {
        navigate({
          pathname: basePath + "/edit/" + selectedItems[0].app_id,
        });
        setAction("Edit");
        setFocusItem(selectedItems[0]);
      } else if (selection) {
        navigate({
          pathname: basePath + "/edit/" + selection.app_id,
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
    (selection: Application[]) => {
      setSelectedItems(selection);
      //Reset URL to base table path.
      navigate({
        pathname: basePath,
      });
    },
    [basePath, navigate]
  );

  const handleEditSave = React.useCallback(
    async (editedItem: Application) => {
      let newApp: Partial<Application> = Object.assign({}, editedItem);
      const app_id = editedItem.app_id;
      const app_name = editedItem.app_name;

      newApp = getChanges(newApp, appLoadingState.data, Schemas.Application.keyAttribute);
      if (!newApp) {
        // no changes to original record.
        addNotification({
          type: "warning",
          dismissible: true,
          header: "Save " + schemaName,
          content: "No updates to save.",
        });
        return;
      }
      delete newApp.app_id;
      const resultEdit = await apiUser.putItem(app_id, newApp, schemaName);

      if (resultEdit["errors"]) {
        console.debug("PUT " + schemaName + " errors");
        console.debug(resultEdit["errors"]);
        const errorsReturned = parsePUTResponseErrors(resultEdit["errors"]).join(",");
        addNotification({
          type: "error",
          dismissible: true,
          header: "Update " + schemaName,
          content: errorsReturned,
        });
      } else {
        addNotification({
          type: "success",
          dismissible: true,
          header: "Update " + schemaName,
          content: app_name + " updated successfully.",
        });
        refreshApps();
        handleResetScreen();

        //This is needed to ensure the item in selectItems reflects new updates
        setSelectedItems([]);
        setFocusItem(undefined);
      }
    },
    [addNotification, appLoadingState.data, handleResetScreen, refreshApps]
  );

  const handleNewSave = React.useCallback(
    async (editedItem: Application) => {
      const newApp: Partial<Application> = Object.assign({}, editedItem);
      const apiUser = new UserApiClient();

      delete newApp.app_id;
      const resultAdd = await apiUser.postItem(newApp, schemaName);

      if (resultAdd["errors"]) {
        console.debug("PUT " + schemaName + " errors");
        console.debug(resultAdd["errors"]);
        const errorsReturned = parsePUTResponseErrors(resultAdd["errors"]).join(",");
        addNotification({
          type: "error",
          dismissible: true,
          header: "Add " + schemaName,
          content: errorsReturned,
        });
      } else {
        addNotification({
          type: "success",
          dismissible: true,
          header: "Add " + schemaName,
          content: newApp.app_name + " added successfully.",
        });
        refreshApps();
        handleResetScreen();
      }
    },
    [addNotification, handleResetScreen, refreshApps]
  );

  async function handleSave(editedItem: Application, action: string) {
    try {
      if (action === "Edit") {
        await handleEditSave(editedItem);
      } else {
        await handleNewSave(editedItem);
      }
    } catch (e) {
      apiActionErrorHandler(action, schemaName, e, addNotification);
    }
  }

  const handleDeleteItemClick = React.useCallback(() => {
    // Check if app's databases and servers have move group assigned
    const assetsWithMoveGroup = selectedItems.flatMap((app) => {
      const dbWithGroups = databaseLoadingState.data
        .filter((db) => app.database_ids?.includes(db.database_id) && db.move_group_id)
        .map((db) => ({
          appName: app.app_name,
          entity: Schemas.Database.friendlyName,
          entityName: db.database_name,
          moveGroupName:
            (db as EntityWithResolvedMoveGroup).__move_group_id ?? `Move group with Id ${db.move_group_id}`,
        }));
      const svrWithGroups = serverLoadingState.data
        .filter((svr) => app.server_ids?.includes(svr.server_id) && svr.move_group_id)
        .map((svr) => ({
          appName: app.app_name,
          entity: Schemas.Server.friendlyName,
          entityName: svr.server_name,
          moveGroupName:
            (svr as EntityWithResolvedMoveGroup).__move_group_id ?? `Move group with Id ${svr.move_group_id}`,
        }));
      return [...dbWithGroups, ...svrWithGroups];
    });

    setAssetsWithMoveGroup(assetsWithMoveGroup);
    if (assetsWithMoveGroup.length) {
      return;
    }

    // Calculate all the assets that only associated to the apps to be deleted
    const appIdToDeleteMap = new Map<string, string>(selectedItems.map((app) => [app.app_id, app.app_name]));
    const isSubsetOfAppIdsToDelete = (appIds: string[]) =>
      appIds.length > 0 && appIds.every((id) => appIdToDeleteMap.has(id));
    const getAppNames = (appIds: string[]) =>
      appIds.map((id) => appIdToDeleteMap.get(id)).filter((x): x is string => !!x);

    const allAssets = {
      [Schemas.Database.name]: databaseLoadingState,
      [Schemas.Server.name]: serverLoadingState,
      ...customAssetLoadingStates,
    };

    const assetsToDelete = Object.entries(allAssets).flatMap(([entity, { data }]) => {
      const nameAttribute = `${entity}_name`;
      const getAppIds = (item: unknown) => [
        ...new Set([getNestedValue(item, "app_ids") ?? []].filter((x): x is string => typeof x === "string")),
      ];

      return data
        .map((item) => ({ ...item, appIds: getAppIds(item) }))
        .filter((item) => isSubsetOfAppIdsToDelete(item.appIds))
        .map((item) => ({
          entity: schemas[entity].friendly_name ?? capitalize(entity),
          entityName: getNestedValue(item, nameAttribute),
          appNames: getAppNames(item.appIds).join(", "),
        }));
    });

    setAssetsCascadeDelete(assetsToDelete);

    setModalVisible(true);
  }, [customAssetLoadingStates, databaseLoadingState, schemas, selectedItems, serverLoadingState]);

  const [isDeleting, setIsDeleting] = React.useState<boolean>(false);
  const [assetsWithMoveGroup, setAssetsWithMoveGroup] = React.useState<AssetsWithMoveGroup[]>([]);
  const [assetsCascadeDelete, setAssetsCascadeDelete] = React.useState<AssetsCascadeDelete[]>([]);

  const handleDeleteItem = React.useCallback(async () => {
    setModalVisible(false);

    const notificationId = addNotification({
      loading: true,
      dismissible: false,
      header: `Deleting ${entityNameInMessage}...`,
    });

    const currentSelectedItems = selectedItems;
    setIsDeleting(true);
    // Clear selected items so as to disable Edit/Edit buttons during deletion
    setSelectedItems([]);

    try {
      await apiTools.cleanupEntities(
        "app",
        selectedItems.map((item) => item.app_id)
      );

      //Create notification where multi select was used.
      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: `Delete ${entityNameInMessage}`,
        content: `${selectedItems.map((item) => item.app_name).join(", ")} ${selectedItems.length > 1 ? "were" : "was"} deleted.`,
      });

      //Unselect applications marked for deletion to clear apps.
      setSelectedItems([]);

      refreshApps();
    } catch (e) {
      console.error(e);
      setSelectedItems(currentSelectedItems);
      addNotification({
        id: notificationId,
        type: "error",
        dismissible: true,
        header: `Delete ${entityNameInMessage}`,
        content: UNEXPECTED_ERROR,
      });
    } finally {
      setIsDeleting(false);
    }
  }, [addNotification, entityNameInMessage, refreshApps, selectedItems]);

  function displayItemsViewScreen() {
    return (
      <SpaceBetween direction="vertical" size="xs">
        <DeletionAlert
          assetsWithMoveGroup={assetsWithMoveGroup}
          onDismiss={() => setAssetsWithMoveGroup([])}
          entityName={entityNameInMessage}
        />
        <ItemTable
          schema={schemas[schemaName]}
          schemaKeyAttribute={Schemas.Application.keyAttribute}
          schemaName={schemaName}
          dataAll={dataAll}
          items={appLoadingState.data}
          selectedItems={selectedItems}
          handleSelectionChange={handleItemSelectionChange}
          isLoading={appLoadingState.isLoading || isDeleting}
          errorLoading={appLoadingState.error}
          handleRefreshClick={handleRefreshClick}
          handleAddItem={handleAddItem}
          handleDeleteItem={handleDeleteItemClick}
          handleEditItem={handleEditItem}
          handleDownloadItems={handleDownloadItems}
          userAccess={userEntityAccess}
        />
        {selectedItems.length === 1 ? (
          <ApplicationView
            schemas={schemas}
            app={selectedItems[0]}
            dataAll={dataAll}
            handleTabChange={setViewCurrentTab}
            selectedTab={viewCurrentTab}
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
          handleSave={handleSave}
          handleCancel={handleResetScreen}
        />
      );
    } else {
      return displayItemsViewScreen();
    }
  }

  React.useEffect(() => {
    if (!appLoadingState.isLoading) {
      const item = appLoadingState.data.find((entry) => {
        return entry.app_id === urlParams.id;
      });

      if (item) {
        // Set list selected item to the item being edited
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
    appLoadingState.data,
    appLoadingState.isLoading,
    handleAddItem,
    handleEditItem,
    location?.pathname,
    selectedItems.length,
    urlParams.id,
  ]);

  //Update help tools panel
  React.useEffect(() => {
    setHelpPanelContentFromSchema(schemas, schemaName);
  }, [schemas, setHelpPanelContentFromSchema]);

  return (
    <div>
      {displayItemsScreen()}
      {modalVisible ? (
        <Modal
          visible={true}
          closeAriaLabel="Close modal"
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button variant="link" onClick={() => setModalVisible(false)}>
                  Cancel
                </Button>
                <Button variant="primary" onClick={handleDeleteItem}>
                  Ok
                </Button>
              </SpaceBetween>
            </Box>
          }
          header="Delete applications"
        >
          {assetsCascadeDelete.length ? (
            <>
              <p>
                The following assets are associated with the selected {entityNameInMessage} only and will be
                automatically deleted along with them.
              </p>
              <EmbeddedTableWithPagination
                items={assetsCascadeDelete}
                sortingDisabled
                columnDefinitions={[
                  {
                    header: "Entity Type",
                    cell: (item) => item.entity,
                  },
                  {
                    header: "Entity Name",
                    cell: (item) => item.entityName,
                  },
                  {
                    header: "Application Names",
                    cell: (item) => item.appNames,
                  },
                ]}
              />
            </>
          ) : null}
          <p>
            Are you sure you wish to delete the {selectedItems.length} selected {entityNameInMessage}?
          </p>
        </Modal>
      ) : (
        <></>
      )}
    </div>
  );
};

export default AppTable;
