/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { ColumnLayout, Container, Header, SpaceBetween, Spinner, Tabs } from "@cloudscape-design/components";

import { NotificationContext } from "../contexts/NotificationContext";
import { ToolsContext } from "../contexts/ToolsContext";
import {
  AppChildProps,
  Application,
  DataLoadingState,
  EntitySchema,
  MoveGroup,
  Wave,
  CustomAsset,
  Database,
  Server,
  WPMJob,
} from "../models";
import ItemTable from "../components/ItemTable";
import ItemAmend from "../components/ItemAmend";
import { capitalize, getChanges } from "../resources/main";
import { useGetItems } from "../actions/ItemsHook";
import { apiActionErrorHandler, parsePUTResponseErrors, UNEXPECTED_ERROR } from "../resources/recordFunctions";
import { CMFModal } from "../components/Modal";
import { exportTable } from "../utils/xlsx-export";
import { ErrorWithType, useErrorHandler } from "../actions/ErrorHandlerHook";
import UserApiClient from "../api_clients/userApiClient";
import { useMFApps } from "../actions/ApplicationsHook";
import { useMFWaves } from "../actions/WavesHook";
import { createCustomEntityType, Schemas } from "../utils/Constants";
import ToolsApiClient from "../api_clients/toolsApiClient";
import { ValueWithLabel } from "../components/ui_attributes/ValueWithLabel";
import Audit from "../components/ui_attributes/Audit";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import { useGetDatabases } from "../actions/DatabasesHook";
import { useGetServers } from "../actions/ServersHook";
import { normalize } from "../utils/schema-utils";

type DataAll = Readonly<{
  app: DataLoadingState<Application>;
  database: DataLoadingState<Database>;
  server: DataLoadingState<Server>;
  move_group: DataLoadingState<MoveGroup>;
  wave: DataLoadingState<Wave>;
  wpm_job: DataLoadingState<WPMJob>;
  [key: string]: DataLoadingState<unknown>;
}>;

const handlePutErrors = (result: { errors: unknown }) => {
  if (result.errors) {
    const errorsReturned = parsePUTResponseErrors(result.errors).join(",");
    throw new ErrorWithType(errorsReturned, "error");
  }
};

const apiUser = new UserApiClient();
const apiTools = new ToolsApiClient();

const UserTableCustomAssets: React.FC<AppChildProps> = (props) => {
  const { addNotification } = React.useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = React.useContext(ToolsContext);
  const handleError = useErrorHandler();
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams<{ assetType: string; id?: string }>();

  // The `assetType` is defined as a mandatory parameter in Route definition so fall back to empty string
  // Extract the schema name from the URL parameter (remove trailing 's')
  const schemaName = React.useMemo(() => {
    const assetType = params.assetType ?? "";
    return assetType.endsWith("s") ? assetType.slice(0, -1) : assetType;
  }, [params.assetType]);

  const idField = React.useMemo(() => `${schemaName}_id` as `${string}_id`, [schemaName]);
  const idsField = React.useMemo(() => `${schemaName}_ids` as `${string}_ids`, [schemaName]);
  const nameField = React.useMemo(() => `${schemaName}_name` as `${string}_name`, [schemaName]);

  // Find the schema definition for this custom asset type
  const enrichedSchema = React.useMemo(() => {
    if (props.schemaIsLoading) return null;

    const schema = props.schemas[schemaName];

    if (!schema || schema.schema_type !== "custom") {
      addNotification({
        type: "error",
        content: `Schema not found for custom asset type: ${schemaName}`,
        dismissible: true,
      });
      return null;
    }
    return enrichSchema(schema, props.schemas[Schemas.Application.name]);
  }, [props.schemaIsLoading, props.schemas, schemaName, addNotification]);

  const schemaFriendlyName = React.useMemo(
    () => enrichedSchema?.friendly_name ?? capitalize(schemaName),
    [enrichedSchema?.friendly_name, schemaName]
  );

  const enrichedSchemas = React.useMemo(
    () =>
      enrichedSchema
        ? {
            ...props.schemas,
            [schemaName]: enrichedSchema,
          }
        : props.schemas,
    [enrichedSchema, props.schemas, schemaName]
  );

  React.useEffect(() => {
    setSelectedItems([]);
    setFocusItem(undefined);
    editingItem.current = false;
    setAction("Add");
  }, [params.assetType]);

  // Get items data using the hook
  const [rawItemsLoadingState, { update: refreshItems }] = useGetItems(schemaName);
  // Custom assets enriched with move group and wave IDs
  const [itemsLoadingState, setItemLoadingState] = React.useState<DataLoadingState<CustomAsset>>({
    data: [],
    isLoading: true,
  });
  const [appLoadingState, { update: updateApps }] = useMFApps<Application>();
  const [databaseLoadingState] = useGetDatabases<Database>();
  const [serverLoadingState] = useGetServers<Server>();
  const [moveGroupLoadingState] = useGetItems<MoveGroup>(Schemas.MoveGroup.name);
  const [waveLoadingState] = useMFWaves<Wave>();
  const [wpmJobLoadingState] = useGetItems<WPMJob>(Schemas.WPMJob.name);

  const refreshApps = React.useCallback(() => updateApps(Schemas.Application.name), [updateApps]);

  React.useEffect(() => {
    setItemLoadingState(
      rawItemsLoadingState.isLoading || appLoadingState.isLoading
        ? { isLoading: true, data: [] }
        : enrichItems(rawItemsLoadingState, appLoadingState)
    );
  }, [appLoadingState, rawItemsLoadingState]);

  const dataAll: DataAll = React.useMemo(
    () => ({
      app: appLoadingState,
      database: databaseLoadingState,
      server: serverLoadingState,
      move_group: moveGroupLoadingState,
      wave: waveLoadingState,
      wpm_job: wpmJobLoadingState,
      [schemaName]: itemsLoadingState,
    }),
    [
      appLoadingState,
      databaseLoadingState,
      itemsLoadingState,
      moveGroupLoadingState,
      schemaName,
      serverLoadingState,
      waveLoadingState,
      wpmJobLoadingState,
    ]
  );

  // Is in add/edit mode
  const editingItem = React.useRef(false);

  // Get base path from the URL, all actions will use this base path
  const basePath = React.useMemo(
    () =>
      location.pathname.split("/").length >= 3
        ? "/" + location.pathname.split("/")[1] + "/" + location.pathname.split("/")[2]
        : "/",
    [location.pathname]
  );

  // Main table state management
  const [selectedItems, setSelectedItems] = React.useState<CustomAsset[]>([]);
  const [focusItem, setFocusItem] = React.useState<CustomAsset>();
  const [viewCurrentTab, setViewCurrentTab] = React.useState("details");

  // Viewer pane state management
  const [action, setAction] = React.useState<"Add" | "Edit">("Add");

  const entityLabel = React.useMemo(
    () => schemaName + (selectedItems.length > 1 ? "s" : ""),
    [selectedItems, schemaName]
  );

  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState<boolean>(false);

  // Handle actions
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
      selectedItems.length > 0 ? selectedItems : itemsLoadingState.data,
      schemaFriendlyName + "s",
      schemaName + "s"
    );
  }, [selectedItems, itemsLoadingState.data, schemaFriendlyName, schemaName]);

  const handleResetScreen = React.useCallback(() => {
    editingItem.current = false;
    navigate({
      pathname: basePath,
    });
  }, [basePath, navigate]);

  const handleEditItem = React.useCallback(
    (selection: CustomAsset | null = null) => {
      editingItem.current = true;
      if (selectedItems.length === 1) {
        navigate({
          pathname: basePath + "/edit/" + selectedItems[0][idField],
        });
        setAction("Edit");
        setFocusItem(selectedItems[0]);
      } else if (selection) {
        navigate({
          pathname: basePath + "/edit/" + selection[idField],
        });
        setAction("Edit");
        setFocusItem(selection);
      }
    },
    [selectedItems, navigate, basePath, idField]
  );

  const handleItemSelectionChange = React.useCallback(
    (selection: CustomAsset[]) => {
      setSelectedItems(selection);
      //Reset URL to base table path.
      navigate({
        pathname: basePath,
      });
    },
    [basePath, navigate]
  );

  const handleRefreshClick = React.useCallback(() => {
    refreshItems(schemaName);
    refreshApps();
  }, [refreshApps, refreshItems, schemaName]);

  const getDataChanges = React.useCallback(
    (assetId: string, asset?: CustomAsset) => {
      // Find out the changed appIds
      const orig = itemsLoadingState.data.find((x) => x[idField] === assetId);
      const origAppIdsSet = new Set((orig?.app_ids ?? []).filter((x): x is string => !!x));
      const updatedAppIdSet = new Set((asset?.app_ids ?? []).filter((x): x is string => !!x));
      const addedAppIds = Array.from(updatedAppIdSet).filter((x) => !origAppIdsSet.has(x));
      const removedAppIds = Array.from(origAppIdsSet).filter((item) => !updatedAppIdSet.has(item));

      return { addedAppIds, removedAppIds };
    },
    [idField, itemsLoadingState.data]
  );

  const handleItemUpdate = React.useCallback(
    (item: CustomAsset) => {
      setFocusItem(enrichItem(item, appLoadingState));
    },
    [appLoadingState]
  );

  // Callback function to update the delta of appIds
  const callApiToUpdateApps = React.useCallback(
    async (assetId: string, params: { addedAppIds: string[]; removedAppIds: string[] }) => {
      // Helper function to update an app's '<custom_asset>_ids'
      const updateApp = async (appId: string, isAdding: boolean) => {
        const app = appLoadingState.data.find((x) => x.app_id === appId);
        if (!app) throw new ErrorWithType(`App ${appId} not found`, "error");

        let assetIds: string[];
        if (isAdding) {
          if (app[idsField]?.includes(assetId)) return;
          assetIds = [...(app[idsField] ?? []), assetId];
        } else {
          if (!app[idsField]?.length || !app[idsField].includes(assetId)) return;
          assetIds = app[idsField].filter((x) => x !== assetId);
        }
        const result = await apiUser.putItem(appId, { [idsField]: assetIds }, Schemas.Application.name);
        handlePutErrors(result);
      };

      // Update all affected apps
      await Promise.all([
        ...params.addedAppIds.map((appId) => updateApp(appId, true)),
        ...params.removedAppIds.map((appId) => updateApp(appId, false)),
      ]);
    },
    [appLoadingState.data, idsField]
  );

  const callApisToSave = React.useCallback(
    async (item: CustomAsset) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let result: any;
      let saved: CustomAsset;
      if (action === "Edit") {
        const changes = getChanges(item, itemsLoadingState.data, idField);
        if (!changes) throw new ErrorWithType("No updates to save.", "warning");

        const itemId = item[idField];
        result = await apiUser.putItem(
          itemId,
          normalize(changes, props.schemas[schemaName], { checkMissingRequiredAttributes: false }),
          schemaName
        );
        handlePutErrors(result);
        saved = item;
      } else {
        result = await apiUser.postItem(normalize(item, props.schemas[schemaName]), schemaName);
        handlePutErrors(result);
        // API return the created item in form of {"[schema]_id: string, [schema]_name: string}
        if (!result?.newItems?.[0]?.[idField]) {
          throw new ErrorWithType(`Failed to create item: Missing ${idField} in response`, "error");
        }
        saved = { [idField]: result.newItems[0][idField], ...item };
      }
      const { addedAppIds, removedAppIds } = getDataChanges(saved[idField], saved);

      // Update apps if there are added appIds or removed appIds
      if (addedAppIds.length > 0 || removedAppIds.length > 0) {
        await callApiToUpdateApps(saved[idField], { addedAppIds, removedAppIds });
      }
    },
    [action, callApiToUpdateApps, getDataChanges, idField, itemsLoadingState.data, props.schemas, schemaName]
  );

  const handleSave = React.useCallback(
    async (editItem: CustomAsset, action: string) => {
      const header = `${action} ${schemaFriendlyName}`;
      const content = `${editItem[nameField]} ${action === "Edit" ? "updated" : "added"} successfully.`;

      const item = Object.assign({}, editItem);
      try {
        await callApisToSave(item);
        addNotification({
          type: "success",
          dismissible: true,
          header,
          content,
        });

        if (action === "Edit") {
          //This is needed to ensure the item in selectItems reflects new updates
          setSelectedItems([]);
          setFocusItem(undefined);
        }

        handleRefreshClick();
        handleResetScreen();
      } catch (e) {
        if (e instanceof ErrorWithType) handleError(e, { header });
        else apiActionErrorHandler(action, schemaName, e, addNotification);
      }
    },
    [
      schemaFriendlyName,
      nameField,
      callApisToSave,
      addNotification,
      handleRefreshClick,
      handleResetScreen,
      handleError,
      schemaName,
    ]
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
        createCustomEntityType(schemaName),
        selectedItems.map((item) => item[idField])
      );

      //Create notification where multi select was used.
      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: `Delete ${entityLabel}`,
        content: `${selectedItems.map((item) => item[nameField]).join(", ")} ${selectedItems.length > 1 ? "were" : "was"} deleted.`,
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
  }, [selectedItems, addNotification, entityLabel, handleRefreshClick, idField, schemaName, nameField]);

  function displayItemsViewScreen(schema: EntitySchema) {
    return (
      <SpaceBetween direction="vertical" size="xs">
        <ItemTable
          schema={schema}
          schemaName={schemaName}
          schemaKeyAttribute={idField}
          dataAll={dataAll}
          items={itemsLoadingState.data || []}
          selectedItems={selectedItems}
          handleSelectionChange={handleItemSelectionChange}
          isLoading={rawItemsLoadingState.isLoading || appLoadingState.isLoading || isDeleting}
          errorLoading={itemsLoadingState.error}
          handleRefreshClick={handleRefreshClick}
          handleAddItem={handleAddItem}
          handleDeleteItem={() => setDeleteConfirmationModalVisible(true)}
          handleEditItem={handleEditItem}
          handleDownloadItems={handleDownloadItems}
          userAccess={props.userEntityAccess}
        />
        {selectedItems.length === 1 ? (
          <CustomAssetView
            schemas={enrichedSchemas}
            schemaName={schemaName}
            asset={selectedItems[0]}
            nameField={nameField}
            dataAll={dataAll}
            selectedTab={viewCurrentTab}
            handleTabChange={setViewCurrentTab}
          />
        ) : undefined}
      </SpaceBetween>
    );
  }

  function displayItemsScreen(schema: EntitySchema) {
    if (editingItem.current) {
      return (
        <ItemAmend
          key={`item-amend-${schemaName}-${action}`}
          action={action}
          schemaName={schemaName}
          schemas={enrichedSchemas}
          userAccess={props.userEntityAccess}
          item={focusItem}
          handleItemUpdate={handleItemUpdate}
          handleSave={handleSave}
          handleCancel={handleResetScreen}
        />
      );
    } else {
      return displayItemsViewScreen(schema);
    }
  }

  // Check URL parameters and update state accordingly
  React.useEffect(() => {
    if (!itemsLoadingState.isLoading && itemsLoadingState.data.length && params.id) {
      const item = itemsLoadingState.data?.find((entry) => {
        return entry[idField] === params.id;
      });

      if (item) {
        // Set the selected item
        setSelectedItems([item]);

        // If we're on an edit path, set the focus item and editing mode
        if (location.pathname.includes("/edit/")) {
          setFocusItem(item);
          editingItem.current = true;
          setAction("Edit");
        }
      }
    } else if (location.pathname.includes("/add")) {
      // Add path detected
      editingItem.current = true;
      setAction("Add");
    }
  }, [location.pathname, params.id, itemsLoadingState.data, itemsLoadingState.isLoading, schemaName, idField]);

  //Update help tools panel
  React.useEffect(() => {
    setHelpPanelContentFromSchema(enrichedSchemas, schemaName);
  }, [enrichedSchemas, schemaName, setHelpPanelContentFromSchema]);

  // Render loading state if schema is not available
  if (props.schemaIsLoading || !enrichedSchema) {
    return <Spinner />;
  }

  return (
    <div key={`custom-asset-container-${schemaName}`}>
      {displayItemsScreen(enrichedSchema)}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={`Delete ${entityLabel}`}
      >
        <p>
          Are you sure you wish to delete the {selectedItems.length} selected {entityLabel}?
        </p>
      </CMFModal>
    </div>
  );
};

export default UserTableCustomAssets;

type CustomAssetViewParams = Readonly<{
  schemas: Record<string, EntitySchema>;
  schemaName: string;
  asset: CustomAsset;
  nameField: `${string}_name`;
  dataAll: DataAll;
  handleTabChange: (arg0: string) => void;
  selectedTab: string;
}>;

const CustomAssetView = ({
  asset,
  nameField,
  dataAll,
  schemaName,
  schemas,
  selectedTab,
  handleTabChange,
}: CustomAssetViewParams) => {
  const schema = React.useMemo(() => schemas[schemaName], [schemaName, schemas]);

  const nameLabel = React.useMemo(() => {
    const nameAttribute = schema.attributes.find((attr) => attr.name === nameField);
    return nameAttribute?.description ?? `${capitalize(schemaName)} Name`;
  }, [nameField, schema?.attributes, schemaName]);

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
              <ColumnLayout columns={2} variant="text-grid">
                <SpaceBetween size="l">
                  <ValueWithLabel label={nameLabel}>{asset[nameField]}</ValueWithLabel>
                  <Audit item={asset} expanded={true} />
                </SpaceBetween>
              </ColumnLayout>
            </Container>
          ),
        },
        {
          label: "All attributes",
          id: "attributes",
          content: (
            <Container header={<Header variant="h2">All attributes</Header>}>
              <SpaceBetween size="l">
                <ColumnLayout columns={2} variant="text-grid">
                  <AllViewerAttributes schema={schemas[schemaName]} schemas={schemas} item={asset} dataAll={dataAll} />
                </ColumnLayout>
                <Audit item={asset} expanded={true} />
              </SpaceBetween>
            </Container>
          ),
        },
      ]}
    />
  );
};

// In MLP only Business Custom Assets (BCA) are supported, which aren't grouped or wave planned
// and the move groups and waves are inferred via apps. Enrich the schema to display them
const enrichSchema = (schema: Readonly<EntitySchema>, appSchema: Readonly<EntitySchema>): EntitySchema => {
  const moveGroupAndWaveIds = appSchema.attributes
    // Extract move_group_ids and wave_ids attributes but ignore group
    .filter((att) => ["move_group_ids", "wave_ids"].includes(att.name));
  return {
    ...schema,
    attributes: [...schema.attributes, ...moveGroupAndWaveIds],
  };
};

const enrichItem = (
  item: Readonly<CustomAsset>,
  appLoadingState: Readonly<DataLoadingState<Application>>
): CustomAsset => {
  const mgIdSet = new Set<string>();
  const waveIdSet = new Set<string>();

  appLoadingState.data
    .filter((app) => item.app_ids?.includes(app.app_id))
    .forEach((app) => {
      app.move_group_ids?.forEach((mgId) => mgIdSet.add(mgId));
      app.wave_ids?.forEach((waveId) => waveIdSet.add(waveId));
    });

  return {
    ...item,
    move_group_ids: Array.from(mgIdSet),
    wave_ids: Array.from(waveIdSet),
  };
};

const enrichItems = (
  itemLoadingState: Readonly<DataLoadingState<CustomAsset>>,
  appLoadingState: Readonly<DataLoadingState<Application>>
): DataLoadingState<CustomAsset> => ({
  ...itemLoadingState,
  data: itemLoadingState.data?.map((item) => enrichItem(item, appLoadingState)) ?? [],
});
