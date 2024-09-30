/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useEffect, useState } from "react";
import UserApiClient from "../api_clients/userApiClient";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import ItemAmend from "../components/ItemAmend";
import { exportTable } from "../utils/xlsx-export";
import { SpaceBetween } from "@cloudscape-design/components";

import PipelineView from "../components/PipelineView";
import { useGetPipelines } from "../actions/PipelinesHook";
import { useGetTaskExecutions } from "../actions/TaskExecutionsHook";
import ItemTable from "../components/ItemTable";
import { apiActionErrorHandler, parsePUTResponseErrors } from "../resources/recordFunctions";
import { NotificationContext } from "../contexts/NotificationContext";
import { EntitySchema } from "../models/EntitySchema";
import { ToolsContext } from "../contexts/ToolsContext";
import { CMFModal } from "../components/Modal";
import { useAutomationScripts } from "../actions/AutomationScriptsHook";

const ViewItem = (props: {
  schema: Record<string, EntitySchema>;
  selectedItems: any[];
  dataAll: any;
  tasksRefresh: any;
  taskExecutionsRefresh: any;
  userEntityAccess: any;
}) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState("details");

  if (props.selectedItems.length === 1) {
    const pipeline = props.selectedItems[0];
    const taskExecutions = props.dataAll.task_execution.data
      .filter((te: any) => te.pipeline_id === pipeline.pipeline_id)
      .sort((a: any, b: any) => a.task_sequence_number - b.task_sequence_number);

    return (
      <div data-testid={"pipeline-details-view"}>
        <PipelineView
          schema={props.schema}
          pipeline={pipeline}
          taskExecutions={taskExecutions}
          handleTabChange={setViewerCurrentTab}
          dataAll={props.dataAll}
          selectedTab={viewerCurrentTab}
          tasksRefresh={props.tasksRefresh}
          taskExecutionsRefresh={props.taskExecutionsRefresh}
          userEntityAccess={props.userEntityAccess}
        />
      </div>
    );
  } else {
    return null;
  }
};

type UserPipelineTableParams = {
  schemas: Record<string, EntitySchema>;
  userEntityAccess: any;
  schemaIsLoading?: boolean;
};
const UserPipelineTable = ({ schemas, userEntityAccess }: UserPipelineTableParams) => {
  const { addNotification } = useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = useContext(ToolsContext);

  let location = useLocation();
  let navigate = useNavigate();
  let params = useParams();

  //Data items for viewer and table.
  const [{ isLoading: isLoadingMain, data: dataMain, error: errorMain }, { update: updateMain }] = useGetPipelines();
  const [
    { isLoading: isLoadingTaskExecutions, data: dataTaskExecutions, error: errorTaskExecutions },
    { update: updateTaskExecutions },
  ] = useGetTaskExecutions();
  const [{ isLoading: isLoadingScripts, data: dataScripts, error: errorScripts }, { update: updateScripts }] =
    useAutomationScripts();

  const dataAll = {
    pipeline: {
      data: dataMain,
      isLoading: isLoadingMain,
      error: errorMain,
    },
    task_execution: {
      data: dataTaskExecutions,
      isLoading: isLoadingTaskExecutions,
      error: errorTaskExecutions,
    },
    script: {
      data: dataScripts,
      isLoading: isLoadingScripts,
      error: errorScripts,
    },
  };

  //Layout state management.
  const [editingItem, setEditingItem] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<Array<any>>([]);
  const [focusItem, setFocusItem] = useState<any>([]);

  //Viewer pane state management.
  const [action, setAction] = useState("Add");

  //Get base path from the URL, all actions will use this base path.
  const basePath = location.pathname.split("/").length >= 2 ? "/" + location.pathname.split("/")[1] : "/";
  //Key for main item displayed in table.
  const itemIDKey = "pipeline_id";
  const schemaName = "pipeline";

  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = useState(false);

  function handleAddItem() {
    navigate({
      pathname: basePath + "/add",
    });
    setAction("Add");
    setFocusItem({});
    setEditingItem(true);
  }

  function handleDownloadItems() {
    if (selectedItems.length > 0) {
      // Download selected only.
      exportTable(selectedItems, "Pipelines", schemaName + "s");
    } else {
      //Download all.
      exportTable(dataMain, "Pipelines", schemaName + "s");
    }
  }

  function handleResetScreen() {
    navigate({
      pathname: basePath,
    });
    setEditingItem(false);
  }

  function handleItemSelectionChange(selection: Array<any>) {
    setSelectedItems(selection);
    if (selection.length === 1) {
      //TODO Need to pull in Waves or other data here.
      //updateApps(selection[0].app_id);
    }
    //Reset URL to base table path.
    navigate({
      pathname: basePath,
    });
  }

  async function handleNewSave(editedItem: any) {
    let newItem = Object.assign({}, editedItem);
    const apiUser = new UserApiClient();

    delete newItem[schemaName + "_id"];
    // Adding default pipeline status after creation (pipeline updates are currently not allowed)
    newItem["pipeline_status"] = "Provisioning";

    let resultAdd = await apiUser.postItem(newItem, schemaName);

    if (resultAdd["errors"]) {
      console.debug("PUT " + schemaName + " errors");
      console.debug(resultAdd["errors"]);
      let errorsReturned = parsePUTResponseErrors(resultAdd["errors"]).join(",");
      addNotification({
        type: "error",
        dismissible: true,
        header: "Add " + schemaName,
        content: errorsReturned,
      });
      return false;
    } else {
      addNotification({
        type: "success",
        dismissible: true,
        header: "Add " + schemaName,
        content: newItem[schemaName + "_name"] + " added successfully.",
      });
      updateMain();
      updateTaskExecutions();
      handleResetScreen();
    }
  }

  async function handleSave(editItem: any, action: string) {
    let newItem = Object.assign({}, editItem);
    try {
      await handleNewSave(newItem);
    } catch (e: any) {
      apiActionErrorHandler(action, schemaName, e, addNotification);
    }
  }

  async function handleRefreshClick() {
    await updateMain();
    await updateTaskExecutions();
  }

  async function handleDeleteItem() {
    setDeleteConfirmationModalVisible(false);

    let currentItem: any = 0;
    let multiReturnMessage = [];
    let notificationId;

    try {
      const apiUser = new UserApiClient();
      if (selectedItems.length > 1) {
        notificationId = addNotification({
          type: "success",
          loading: true,
          dismissible: false,
          header: "Deleting selected " + schemaName + "s...",
        });
      }

      for (let item in selectedItems) {
        currentItem = item;
        await apiUser.deletePipeline(selectedItems[item][schemaName + "_id"]);
        //Combine notifications into a single message if multi selected used, to save user dismiss clicks.
        if (selectedItems.length > 1) {
          multiReturnMessage.push(selectedItems[item][schemaName + "_name"]);
        } else {
          addNotification({
            type: "success",
            dismissible: true,
            header: schemaName + " deleted successfully",
            content: selectedItems[item][schemaName + "_name"] + " was deleted.",
          });
        }
      }

      //Create notification where multi select was used.
      if (selectedItems.length > 1) {
        addNotification({
          id: notificationId,
          type: "success",
          dismissible: true,
          header: schemaName + " deleted successfully",
          content: multiReturnMessage.join(", ") + " were deleted.",
        });
      }

      // Unselect pipelines marked for deletion to clear apps.
      setSelectedItems([]);
      await updateMain();
    } catch (e: any) {
      console.log(e);
      addNotification({
        type: "error",
        dismissible: true,
        header: schemaName + " deletion failed",
        content: selectedItems[currentItem][schemaName + "_name"] + " failed to delete.",
      });
    }
  }

  function displayItemsViewScreen() {
    return (
      <SpaceBetween direction="vertical" size="xs">
        <ItemTable
          schema={schemas[schemaName]}
          schemaKeyAttribute={itemIDKey}
          schemaName={schemaName}
          dataAll={dataAll}
          items={dataMain}
          selectedItems={selectedItems}
          handleSelectionChange={handleItemSelectionChange}
          isLoading={isLoadingMain}
          errorLoading={errorMain}
          handleRefreshClick={handleRefreshClick}
          handleAddItem={handleAddItem}
          handleDeleteItem={async function () {
            setDeleteConfirmationModalVisible(true);
          }}
          handleDownloadItems={handleDownloadItems}
          userAccess={userEntityAccess}
        />
        <ViewItem
          schema={schemas}
          selectedItems={selectedItems}
          dataAll={dataAll}
          taskExecutionsRefresh={updateTaskExecutions}
          tasksRefresh={updateScripts}
          userEntityAccess={userEntityAccess}
        />
      </SpaceBetween>
    );
  }

  function displayItemsScreen() {
    if (editingItem) {
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

  useEffect(() => {
    let selected = [];

    if (!isLoadingMain) {
      let item = dataMain.filter(function (entry: any) {
        return entry[itemIDKey] === params.id;
      });

      if (item.length === 1) {
        selected.push(item[0]);
        handleItemSelectionChange(selected);
      } else if (location?.pathname.match("/add")) {
        //Add url used, redirect to add screen.
        handleAddItem();
      }
    }
  }, [dataMain]);

  //Update help tools panel.
  useEffect(() => {
    setHelpPanelContentFromSchema(schemas, schemaName);
  }, [schemas]);

  return (
    <div>
      {displayItemsScreen()}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={"Delete pipelines"}
      >
        <p>Are you sure you wish to delete the {selectedItems.length} selected pipelines?</p>
      </CMFModal>
    </div>
  );
};

// Component TableView is a skeleton of a Table using AWS-UI React components.
export default UserPipelineTable;
