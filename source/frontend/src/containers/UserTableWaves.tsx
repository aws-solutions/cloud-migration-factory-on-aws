/* eslint-disable @typescript-eslint/no-explicit-any */
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ButtonDropdownProps, SpaceBetween } from "@cloudscape-design/components";

import ItemAmend from "../components/ItemAmend";
import ItemTable from "../components/ItemTable";
import { CMFModal } from "../components/Modal";
import { WaveDetailsView } from "../components/WaveView";

import { NotificationContext } from "../contexts/NotificationContext";
import { ToolsContext } from "../contexts/ToolsContext";
import { useMFApps } from "../actions/ApplicationsHook";
import { useAutomationJobs } from "../actions/AutomationJobsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import {
  Application,
  Database,
  DataLoadingState,
  EntitySchema,
  Job,
  MoveGroup,
  Server,
  UserAccess,
  Wave,
  WPMJob,
} from "../models";
import { getChanges, userAutomationActionsMenuItems } from "../resources/main";
import { apiActionErrorHandler, parsePUTResponseErrors, UNEXPECTED_ERROR } from "../resources/recordFunctions";
import { Schemas } from "../utils/Constants";
import { exportTable } from "../utils/xlsx-export";
import ToolsApiClient from "../api_clients/toolsApiClient";
import UserApiClient from "../api_clients/userApiClient";
import { ErrorWithType, useErrorHandler } from "../actions/ErrorHandlerHook";
import { useGetItems } from "../actions/ItemsHook";
import AutomationTools from "../components/AutomationTools";
import { useGetDatabases } from "../actions/DatabasesHook";

type UserWaveTableParams = {
  readonly userEntityAccess: UserAccess;
  readonly schemas: Record<string, EntitySchema>;
};

type DataAll = {
  readonly app: DataLoadingState<Application>;
  readonly database: DataLoadingState<Database>;
  readonly server: DataLoadingState<Server>;
  readonly move_group: DataLoadingState<MoveGroup>;
  readonly wave: DataLoadingState<Wave>;
  readonly wpm_job: DataLoadingState<WPMJob>;
  readonly job: DataLoadingState<Job>;
};

const schemaName = Schemas.Wave.name;
const apiUser = new UserApiClient();
const apiTools = new ToolsApiClient();

const handlePutErrors = (result: any) => {
  if (result?.errors) {
    const errorsReturned = parsePUTResponseErrors(result.errors).join(",");
    throw new ErrorWithType(errorsReturned, "error");
  }
};

const UserWaveTable = ({ schemas, userEntityAccess }: UserWaveTableParams) => {
  const { addNotification } = React.useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = React.useContext(ToolsContext);
  const handleError = useErrorHandler();

  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  //Data items for viewer and table.
  //Data items for viewer and table.
  const [appLoadingState, { update: updateApps }] = useMFApps<Application>();
  const [databaseLoadingState, { update: refreshDatabases }] = useGetDatabases<Database>();
  const [serverLoadingState, { update: refreshServers }] = useGetServers<Server>();
  const [moveGroupLoadingState, { update: updateMoveGroups }] = useGetItems<MoveGroup>(Schemas.MoveGroup.name);
  const [waveLoadingState, { update: updateWaves }] = useMFWaves<Wave>();
  const [wpmJobLoadingState] = useGetItems<WPMJob>(Schemas.WPMJob.name);
  const [autoJobLoadingState] = useAutomationJobs();

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
      job: autoJobLoadingState,
    }),
    [
      appLoadingState,
      autoJobLoadingState,
      databaseLoadingState,
      moveGroupLoadingState,
      serverLoadingState,
      waveLoadingState,
      wpmJobLoadingState,
    ]
  );

  //Main table state management.
  const [selectedItems, setSelectedItems] = React.useState<Wave[]>([]);
  const [focusItem, setFocusItem] = React.useState<Wave>();
  const [viewCurrentTab, setViewCurrentTab] = React.useState("details");

  const entityLabel = React.useMemo(() => schemaName + (selectedItems.length > 1 ? "s" : ""), [selectedItems]);

  //Viewer pane state management.
  const [action, setAction] = React.useState("View");
  const [actions, setActions] = React.useState<ButtonDropdownProps.ItemOrGroup[]>([]); //Actions menu dropdown options.
  const [automationAction, setAutomationAction] = React.useState<string | undefined>(undefined);

  const [preformingAction, setPreformingAction] = React.useState(false);

  //Get base path from the URL, all actions will use this base path.
  const basePath = React.useMemo(
    () => (location.pathname.split("/").length >= 2 ? "/" + location.pathname.split("/")[1] : "/"),
    [location.pathname]
  );

  //Modals
  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState<boolean>(false);

  const handleRefreshClick = React.useCallback(() => {
    refreshWaves();
    refreshMoveGroups();
    refreshServers();
    refreshDatabases();
    refreshApps();
  }, [refreshApps, refreshDatabases, refreshMoveGroups, refreshServers, refreshWaves]);

  const handleAddItem = React.useCallback(() => {
    navigate({
      pathname: basePath + "/add",
    });
    setAction("Add");
    setFocusItem(undefined);
  }, [basePath, navigate]);

  const handleDownloadItems = React.useCallback(() => {
    exportTable(selectedItems.length > 0 ? selectedItems : waveLoadingState.data, "Waves", "waves");
  }, [selectedItems, waveLoadingState.data]);

  const handleEditItem = React.useCallback(
    (selection: Wave | null = null) => {
      if (selectedItems.length === 1) {
        navigate({
          pathname: basePath + "/edit/" + selectedItems[0].wave_id,
        });
        setAction("Edit");
        setFocusItem(selectedItems[0]);
      } else if (selection) {
        navigate({
          pathname: basePath + "/edit/" + selection.wave_id,
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
    (selection: Wave[]) => {
      setSelectedItems(selection);
      //Reset URL to base table path.
      navigate({
        pathname: basePath,
      });
    },
    [basePath, navigate]
  );

  const handleAction = React.useCallback(
    async (actionData: any, actionId: number) => {
      if (!automationAction) return;

      setPreformingAction(true);

      const newItem = Object.assign({}, actionData);
      let notificationId;

      const apiAction =
        schemas[automationAction].actions?.filter((entry: { id: number }) => entry.id === actionId) ?? [];

      if (apiAction.length !== 1) {
        addNotification({
          type: "error",
          dismissible: true,
          header: "Perform wave action",
          content: schemas[automationAction].friendly_name + " action [" + actionId + "] not found in schema.",
        });
      } else {
        try {
          if (apiAction[0].additionalData) {
            const keys = Object.keys(apiAction[0].additionalData);
            for (const i in keys) {
              newItem[keys[i]] = apiAction[0].additionalData[keys[i]];
            }
          }

          notificationId = addNotification({
            loading: true,
            dismissible: false,
            header: "Perform wave action",
            content: "Performing action - " + apiAction[0].name,
          });

          const apiTools = new ToolsApiClient();
          const response = await apiTools.postTool(apiAction[0].apiPath, newItem);

          //Extra UUID from response.
          let uuid = response.split("+");
          if (uuid.length > 1) {
            uuid = uuid[1];
            handleResetScreen();

            addNotification({
              id: notificationId,
              type: "success",
              dismissible: true,
              header: "Perform wave action",
              actionButtonTitle: "View Job",
              actionButtonLink: "/automation/jobs/" + uuid,
              content: apiAction[0].name + " action successfully.",
            });
          } else {
            handleResetScreen();

            addNotification({
              id: notificationId,
              type: "success",
              dismissible: true,
              header: "Perform wave action",
              content: response,
            });
          }
        } catch (e: any) {
          console.log(e);
          const content =
            apiAction[0].name +
            " action failed: " +
            (e.response.data?.cause || e.response.data || e.message || "action failed: Unknown error occurred");

          addNotification({
            id: notificationId,
            type: "error",
            dismissible: true,
            header: "Perform wave action",
            content: content,
          });
        }
      }

      setPreformingAction(false);
    },
    [addNotification, automationAction, handleResetScreen, schemas]
  );

  const callApisToSave = React.useCallback(
    async (w: Wave) => {
      let result: any;
      // Create/update move group
      if (action === "Add") {
        result = await apiUser.postItem(w, Schemas.Wave.name);
      } else {
        const changes = getChanges(w, waveLoadingState.data, Schemas.Wave.keyAttribute);
        if (!changes) throw new ErrorWithType("No updates to save.", "warning");

        result = await apiUser.putItem(w.wave_id, changes, Schemas.Wave.name);
      }
      handlePutErrors(result);
    },
    [action, waveLoadingState.data]
  );

  const handleSave = React.useCallback(
    async (editItem: Wave, action: string) => {
      const header = `${action} ${Schemas.Wave.name}`;

      const item = Object.assign({}, editItem);
      try {
        if (action === "Edit") {
          await callApisToSave(item);
          addNotification({
            type: "success",
            dismissible: true,
            header,
            content: item.wave_name + " updated successfully.",
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
            content: item.wave_name + " added successfully.",
          });
        }
        handleRefreshClick();
        handleResetScreen();
      } catch (e) {
        if (e instanceof ErrorWithType) handleError(e, { header });
        else apiActionErrorHandler(action, Schemas.Wave.name, e, addNotification);
      }
    },
    [handleRefreshClick, handleResetScreen, callApisToSave, addNotification, handleError]
  );

  const handleActionsClick = React.useCallback(
    (e: { detail: ButtonDropdownProps.ItemClickDetails }) => {
      const action = e.detail.id;

      // Action button dropdown only enabled when one item is selected.
      setFocusItem(selectedItems[0]);
      setAutomationAction(action);
      setAction("Action");
    },
    [selectedItems]
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
        "wave",
        selectedItems.map((item) => item.wave_id)
      );

      //Create notification where multi select was used.
      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: `Delete ${entityLabel}`,
        content: `${selectedItems.map((item) => item.wave_name).join(", ")} ${selectedItems.length > 1 ? "were" : "was"} deleted.`,
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

  //Update actions button options on schema change.
  React.useEffect(() => {
    setActions(userAutomationActionsMenuItems(schemas, userEntityAccess));
  }, [schemas, userEntityAccess]);

  //Update help tools panel.
  React.useEffect(() => {
    setHelpPanelContentFromSchema(schemas, schemaName);
  }, [schemas, setHelpPanelContentFromSchema]);

  function provideContent(currentAction: string) {
    switch (currentAction) {
      case "Action":
        if (!automationAction) return <></>;
        return (
          <AutomationTools
            schemaName={automationAction}
            schema={schemas[automationAction]}
            userAccess={userEntityAccess}
            schemas={schemas}
            performingAction={preformingAction}
            selectedItems={selectedItems}
            handleAction={handleAction}
            handleCancel={handleResetScreen}
          />
        );
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
              schemaKeyAttribute={Schemas.Wave.keyAttribute}
              schemaName={schemaName}
              dataAll={dataAll}
              items={waveLoadingState.data}
              selectedItems={selectedItems}
              handleSelectionChange={handleItemSelectionChange}
              isLoading={waveLoadingState.isLoading || isDeleting}
              errorLoading={waveLoadingState.error}
              handleRefreshClick={handleRefreshClick}
              handleAddItem={handleAddItem}
              handleAction={handleActionsClick}
              actionItems={actions}
              handleDeleteItem={async function () {
                setDeleteConfirmationModalVisible(true);
              }}
              handleEditItem={handleEditItem}
              handleDownloadItems={handleDownloadItems}
              userAccess={userEntityAccess}
            />
            <WaveDetailsView
              schemas={schemas}
              selectedItems={selectedItems}
              dataAll={dataAll}
              handleTabChange={setViewCurrentTab}
              selectedTab={viewCurrentTab}
            />
          </SpaceBetween>
        );
    }
  }

  React.useEffect(() => {
    if (!waveLoadingState.isLoading) {
      const item = waveLoadingState.data.find((entry) => entry.wave_id === params.id);

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
    waveLoadingState.data,
    waveLoadingState.isLoading,
  ]);

  return (
    <div>
      {provideContent(action)}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={"Delete waves"}
      >
        <p>
          Are you sure you wish to delete the {selectedItems.length} selected {entityLabel}?
        </p>
      </CMFModal>
    </div>
  );
};
export default UserWaveTable;
