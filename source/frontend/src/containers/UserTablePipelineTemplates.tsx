/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useEffect, useState } from "react";
import UserApiClient from "../api_clients/userApiClient";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { exportTable } from "../utils/xlsx-export";
import { SpaceBetween } from "@cloudscape-design/components";

import PipelineTemplateView from "../components/PipelineTemplateView";
import { useGetPipelineTemplates } from "../actions/PipelineTemplatesHook";
import { useGetPipelines } from "../actions/PipelinesHook";
import { useGetPipelineTemplateTasks } from "../actions/PipelineTemplateTasksHook";
import { useGetTaskExecutions } from "../actions/TaskExecutionsHook";
import ItemTable from "../components/ItemTable";
import { apiActionErrorHandler, parsePUTResponseErrors } from "../resources/recordFunctions";
import { NotificationContext } from "../contexts/NotificationContext";
import ItemAmend from "../components/ItemAmend";
import { getChanges } from "../resources/main";

import { EntitySchema } from "../models/EntitySchema";
import { ToolsContext } from "../contexts/ToolsContext";
import { CMFModal } from "../components/Modal";
import { PipelineTemplate } from "../models/PipelineTemplate";
import { ClickEvent } from "../models/Events.ts";
import { useAutomationScripts } from "../actions/AutomationScriptsHook";
import ToolsApiClient from "../api_clients/toolsApiClient.ts";

type ViewPipelineTemplateParams = {
  schema: Record<string, EntitySchema>;
  selectedItems: any[];
  dataAll: any;
  updatePipelineTemplateTasks: any;
  errorPipelineTemplateTasks?: any;
  isLoadingPipelineTemplateTasks?: boolean;
  userEntityAccess: any;
  schemaIsLoading?: boolean;
};

const ViewItem = (props: ViewPipelineTemplateParams) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState("details");

  if (props.selectedItems.length === 1) {
    const pipelineTemplate = props.selectedItems[0];
    const pipelineTemplateTasks = props.dataAll.pipeline_template_task.data
      .filter((ptt: any) => ptt.pipeline_template_id === pipelineTemplate.pipeline_template_id)
      .sort((a: any, b: any) => a.task_sequence_number - b.task_sequence_number);

    return (
      <PipelineTemplateView
        schema={props.schema}
        pipelineTemplate={pipelineTemplate}
        pipelineTemplateTasks={pipelineTemplateTasks}
        handleTabChange={setViewerCurrentTab}
        dataAll={props.dataAll}
        selectedTab={viewerCurrentTab}
        pipelineTemplateTasksRefresh={props.updatePipelineTemplateTasks}
        userEntityAccess={props.userEntityAccess}
      />
    );
  } else {
    return null;
  }
};

type UserPipelineTemplateTableParams = {
  schemas: Record<string, EntitySchema>;
  userEntityAccess: any;
  schemaIsLoading?: boolean;
};

const UserPipelineTemplateTable = ({ schemas, userEntityAccess }: UserPipelineTemplateTableParams) => {
  const { addNotification } = useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = useContext(ToolsContext);

  let location = useLocation();
  let navigate = useNavigate();
  let params = useParams();

  //Data items for viewer and table.
  const [{ isLoading: isLoadingMain, data: dataMain, error: errorMain }, { update: updateMain }] =
    useGetPipelineTemplates();
  const [{ isLoading: isLoadingPipelines, data: dataPipelines, error: errorPipelines }] = useGetPipelines();
  const [
    { isLoading: isLoadingPipelineTemplateTasks, data: dataPipelineTemplateTasks, error: errorPipelineTemplateTasks },
    { update: updatePipelineTemplateTasks },
  ] = useGetPipelineTemplateTasks();
  const [{ isLoading: isLoadingTaskExecutions, data: dataTaskExecutions, error: errorTaskExecutions }] =
    useGetTaskExecutions();
  const [{ isLoading: isLoadingScripts, data: dataScripts, error: errorScripts }] = useAutomationScripts();

  const dataAll = {
    pipeline_template: {
      data: dataMain,
      isLoading: isLoadingMain,
      error: errorMain,
    },
    pipeline: {
      data: dataPipelines,
      isLoading: isLoadingPipelines,
      error: errorPipelines,
    },
    pipeline_template_task: {
      data: dataPipelineTemplateTasks,
      isLoading: isLoadingPipelineTemplateTasks,
      error: errorPipelineTemplateTasks,
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
  const [action, setAction] = useState<string>("Add");

  //Get base path from the URL, all actions will use this base path.
  const basePath = location.pathname.split("/").length >= 2 ? "/" + location.pathname.split("/")[1] : "/";
  //Key for main item displayed in table.
  const itemIDKey = "pipeline_template_id";
  const schemaName = "pipeline_template";

  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = useState(false);
  const isOnlyOneSelected = selectedItems ? selectedItems.length === 1 : false;
  const isDeletionProtected = ((item: PipelineTemplate): boolean => item?.deletion_protection ? item.deletion_protection : false);

  function isErrorResponse(response: any): response is { errors?: boolean } {
    if (response && typeof response === "object") {
      if ("errors" in response) {
        return true;
      }
    }
    return false;
  }

  function handleAddItem() {
    navigate({
      pathname: basePath + "/add",
    });
    setAction("Add");
    setFocusItem({});
    setEditingItem(true);
  }

  async function handleDeleteItem() {
    setDeleteConfirmationModalVisible(false);

    let multiReturnMessage = [];
    let notificationId;

    try {
      const apiUser = new UserApiClient();
      if (selectedItems.length >= 1) {
        if (selectedItems.some((item) => isDeletionProtected(item))) {
          addNotification({
            type: "warning",
            dismissible: true,
            header: "Delete " + schemaName,
            content: "Deletion protection is enabled on this item.",
          });
          return;
        } else {
          notificationId = addNotification({
            type: "success",
            loading: true,
            dismissible: false,
            header: "Deleting selected " + schemaName + "s...",
          });
        }
      }

      for (let item in selectedItems) {
        await apiUser.deletePipelineTemplate(selectedItems[item].pipeline_template_id);
        await handleDeletePipelineTemplateTasks(selectedItems[item].pipeline_template_id);
        //Combine notifications into a single message if multi selected used, to save user dismiss clicks.
        if (selectedItems.length > 1) {
          multiReturnMessage.push(selectedItems[item].pipeline_template_name);
        }
      }

      //Create notification where multi select was used.
      if (selectedItems.length > 1) {
        addNotification({
          id: notificationId,
          type: "success",
          dismissible: true,
          header: "Pipeline templates deleted successfully",
          content: multiReturnMessage.join(", ") + " were deleted.",
        });
      } else {
        addNotification({
          type: "success",
          dismissible: true,
          header: "Pipeline template deleted successfully",
          content: selectedItems[0].pipeline_template_name + " was deleted.",
        });
      }

      //Unselect applications marked for deletion to clear apps.
      setSelectedItems([]);
      await updateMain();
    } catch (e: any) {
      apiActionErrorHandler("Delete", "Pipeline template", e, addNotification);
    }
  }

  // look up the list of pipeline_template_tasks related
  // to the pipeline_template_id and deletes them.
  async function handleDeletePipelineTemplateTasks(pipelineTemplateId: string) {
    try {
      const apiUser = new UserApiClient();
      const resp = await apiUser.getPipelineTemplateTasks();
      const pipelineTemplateTasks = resp
        .filter((ptt: PipelineTemplate) => ptt.pipeline_template_id === pipelineTemplateId)
        .sort((a: any, b: any) => a.task_sequence_number - b.task_sequence_number);

      for (let task of pipelineTemplateTasks) {
        await apiUser.deletePipelineTemplateTask(task.pipeline_template_task_id);
      }
    } catch (e: any) {
      console.error(e);
      addNotification({
        type: "error",
        dismissible: true,
        header: "PipelineTemplateTasks deletion failed",
        content: "Failed to delete PipelineTemplateTasks for PipelineTemplateId: " + pipelineTemplateId,
      });
    }
  }

  function handleEditItem() {
    if (isOnlyOneSelected) {
      navigate({
        pathname: basePath + "/edit/" + selectedItems[0][itemIDKey],
      });
      setAction("Edit");
      setFocusItem(selectedItems[0]);
      setEditingItem(true);
    }
  }

  function handleResetScreen() {
    setEditingItem(false);
    navigate({
      pathname: basePath,
    });
  }

  function handleDuplicateItem() {
    if (isOnlyOneSelected) {
      navigate({
        pathname: basePath + "/duplicate/" + selectedItems[0][itemIDKey],
      });

      setAction("Duplicate");
      setFocusItem(selectedItems[0]);
      setEditingItem(true);
    } else {
      addNotification({
        type: "warning",
        dismissible: true,
        header: "Duplicate " + schemaName,
        content: "Only one item can be duplicated at a time.",
      });
    }
  }

  function handleDownloadItems() {
    if (selectedItems.length > 0) {
      // Download selected only.
      exportTable(selectedItems, "PipelineTemplates", schemaName + "s");
    } else {
      //Download all.
      exportTable(dataMain, "PipelineTemplates", schemaName + "s");
    }
  }

  function handleItemSelectionChange(selection: Array<any>) {
    setSelectedItems(selection);
    //Reset URL to base table path.
    navigate({
      pathname: basePath,
    });
  }

  async function handleAddSave(currentItem: PipelineTemplate, action: string): Promise<void> {
    const { version, pipeline_template_id, ...newPipelineTemplate } = currentItem;

    // create a brand new pipeline template
    const apiUser = new UserApiClient();
    let addResult = await apiUser.postItem(newPipelineTemplate, schemaName);
    // this is to cover Unit Test not returning the response body after post
    if (typeof addResult === "string" && !addResult) {
      addResult = { newItems: [newPipelineTemplate] };
    }

    if (isErrorResponse(addResult)) {
      handleSaveError(addResult, action);
    } else {
      handleSaveSuccess(addResult.newItems, action);
    }
  }

  async function handleEditSave(currentItem: any, action: string) {
    // edit is not permitted for items created by System
    if (isDeletionProtected(currentItem)) {
      addNotification({
        type: "warning",
        dismissible: true,
        header: "Edit " + schemaName,
        content: "Protection is configured for this item.",
      });
      return;
    }

    let newPipelineTemplate = { ...currentItem };
    const pipeline_template_id = newPipelineTemplate.pipeline_template_id;

    // get the changes in the edit to be applied
    newPipelineTemplate = getChanges(newPipelineTemplate, dataMain, "pipeline_template_id");
    if (!newPipelineTemplate) {
      // no changes to original record.
      addNotification({
        type: "warning",
        dismissible: true,
        header: "Edit " + schemaName,
        content: "No updates to save.",
      });
      return;
    }
    delete newPipelineTemplate.pipeline_template_id;
    const apiUser = new UserApiClient();
    let editResult = await apiUser.putItem(pipeline_template_id, newPipelineTemplate, "pipeline_template");

    if (editResult["errors"]) {
      let errorsReturned = parsePUTResponseErrors(editResult["errors"]).join(",");
      addNotification({
        type: "error",
        dismissible: true,
        header: `${action} ${schemaName}`,
        content: errorsReturned,
      });
    } else {
      addNotification({
        type: "success",
        dismissible: true,
        header: "Update " + schemaName,
        content: currentItem.pipeline_template_name + " updated successfully",
      });
      await updateMain();
      handleResetScreen();

      //This is needed to ensure the item in selectItems reflects new updates
      setSelectedItems([]);
      setFocusItem({});
    }
  }

  async function handleSave(currentItem: any, action: string) {
    if (!currentItem) {
      // no changes to original record.
      addNotification({
        type: "warning",
        dismissible: true,
        header: "Save " + schemaName,
        content: "No updates to save.",
      });
      handleResetScreen();
      return;
    }

    // make a local copy of the item to avoid mutating the original object
    // which would then trigger the table to re-render and reset the dirty flag
    if (action && action === "Duplicate") {
      try {
        await handleDuplicateSave(currentItem);
      } catch (e: any) {
        apiActionErrorHandler(action, schemaName, e, addNotification);
      }
    } else if (action && action === "Edit") {
      try {
        await handleEditSave(currentItem, action);
      } catch (e: any) {
        apiActionErrorHandler(action, schemaName, e, addNotification);
      }
    } else if (action && action === "Add") {
      try {
        await handleAddSave(currentItem, action);
      } catch (e: any) {
        apiActionErrorHandler(action, schemaName, e, addNotification);
      }
    } else {
      console.error("Unknown action: " + action);
    }
  }

  function handleSaveError(result: any, action: string) {
    // we enter this function if result["errors"] exist,
    // don't need to check it again.
    apiActionErrorHandler(action, schemaName, result["errors"], addNotification);
    let errorsReturned = parsePUTResponseErrors(result["errors"]).join(",");
    addNotification({
      type: "error",
      dismissible: true,
      header: action + " " + schemaName,
      content: errorsReturned,
    });
  }

  function handleSaveSuccess(currentItem: any, action: string) {
    let pipelineTemplateTaskNames: string[] = [];
    let pipelineTemplateNames: string[] = [];
    if (currentItem !== null && Array.isArray(currentItem) && currentItem.length > 0) {
      for (const element of currentItem) {
        element.pipeline_template_task_name && pipelineTemplateTaskNames.push(element.pipeline_template_task_name);
        element.pipeline_template_name && pipelineTemplateNames.push(element.pipeline_template_name);
      }
    }

    let names = "";
    if (pipelineTemplateNames.length > 0) {
      names = names + pipelineTemplateNames.join(", ");
    }
    if (pipelineTemplateTaskNames.length > 0) {
      names = names + pipelineTemplateTaskNames.join(", ");
    }

    const opted = action === "Duplicate" ? action + "d" : action + "ed";
    const content = `${names} ${names.includes(", ") ? "were" : "was"} ${opted} successfully`;
    addNotification({
      type: "success",
      dismissible: true,
      header: `${action} ${schemaName}`,
      content: content,
    });

    updateMain();
    handleResetScreen();

    //This is needed to ensure the item in selectItems reflects new updates
    setSelectedItems([]);
    setFocusItem({});
  }

  async function handleRefreshClick() {
    await updateMain();
    await updatePipelineTemplateTasks();
  }

  async function handleDuplicateSave(currentItem: PipelineTemplate): Promise<void> {
    const {version, pipeline_template_id, deletion_protection, _history, ...newPipelineTemplate} = currentItem;

    const toolsApiClient = new ToolsApiClient();
    let exportData = undefined;
    if (selectedItems.length === 1) {
      const notificationId = addNotification({
        type: "in-progress",
        dismissible: true,
        header: "Pipeline Template duplication",
        content:
          "Duplicating Pipeline Template: " + selectedItems[0].pipeline_template_name,
      });

      try {
        // export current pipeline template.
        exportData = await toolsApiClient.getPipelineTemplateExport(
            selectedItems.map((item: any) => {
              return item["pipeline_template_id"];
            })
        );

        // import updated pipeline template.
        await toolsApiClient.postPipelineTemplateImport([{...exportData[0], ...currentItem}]);

      } catch (e: any) {
        console.error(e);
        addNotification({
          id: notificationId,
          type: "error",
          dismissible: true,
          header: "Pipeline Template duplication",
          content:
            "Failed to duplicate Pipeline Template: " + currentItem.pipeline_template_name + e,
        });
      return;
      }

      await updateMain();
      await updatePipelineTemplateTasks();

      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: "Pipeline Template duplication",
        content: "Duplicated Pipeline Template: " + currentItem.pipeline_template_name,
      });

      handleResetScreen();

      //This is needed to ensure the item in selectItems reflects new updates
      setSelectedItems([]);
      setFocusItem({});
    }
  }

  async function handleDataExport() {
    const toolsApiClient = new ToolsApiClient();
    let exportData;
    if (selectedItems.length > 0) {
      exportData = await toolsApiClient.getPipelineTemplateExport(
        selectedItems.map((item: any) => {
          return item["pipeline_template_id"];
        })
      );
    } else {
      exportData = await toolsApiClient.getPipelineTemplatesExport();
    }

    const blob = new Blob([JSON.stringify(exportData,null, 4)], {
      type: "application/json",
    });

    // Create a temporary URL for the Blob
    const url = window.URL.createObjectURL(blob);

    // Create a temporary anchor element to trigger the file download
    const a = document.createElement("a");
    a.href = url;
    a.download = `pipeline-template-export-${new Date().toISOString()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  async function handleActionSelection(e: ClickEvent) {
    let action = e.detail.id;

    switch (action) {
      case "pipelineImportButton":
        navigate({
          pathname: basePath + "/import",
        });
        break;
      case "pipelineExportButton":
        await handleDataExport();
        break;
      case "pipelineTemplateDuplicateButton":
        handleDuplicateItem();
        break;
      default: {
        console.error("Action not implemented", e.detail);
      }
    }
  }

  function displayItemsViewScreen() {
    const hasWritePermissions = userEntityAccess[schemaName]?.create ?? false;
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
          handleEditItem={handleEditItem}
          handleDownloadItems={handleDownloadItems}
          userAccess={userEntityAccess}
          handleAction={handleActionSelection}
          actionsButtonDisabled={false}
          actionItems={[
            {
              id: "pipelineExportButton",
              text: "Export",
              description: "Export pipeline templates to JSON file",
              disabled: false,
            },
            {
              id: "pipelineImportButton",
              text: "Import",
              description: "Import pipeline templates from JSON file",
              disabled: !hasWritePermissions,
            },
            {
              id: "pipelineTemplateDuplicateButton",
              text: "Duplicate",
              description: "Duplicate a selected pipeline template from JSON file",
              disabled: !hasWritePermissions || !isOnlyOneSelected,
            },
          ]}
        />
        <ViewItem
          schema={schemas}
          selectedItems={selectedItems}
          dataAll={dataAll}
          updatePipelineTemplateTasks={updatePipelineTemplateTasks}
          isLoadingPipelineTemplateTasks={isLoadingPipelineTemplateTasks}
          errorPipelineTemplateTasks={errorPipelineTemplateTasks}
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
        //Check if URL contains duplicate path and switch to amend component.
        if (location?.pathname.match("/Duplicate/")) {
          handleDuplicateItem();
        }
      }
    }
  }, [
    dataMain,
    handleAddItem,
    handleDuplicateItem,
    handleItemSelectionChange,
    isLoadingMain,
    location?.pathname,
    params.id,
  ]);

  //Update help tools panel.
  useEffect(() => {
    setHelpPanelContentFromSchema(schemas, schemaName);
  }, [schemas, setHelpPanelContentFromSchema]);

  return (
    <div>
      {displayItemsScreen()}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={"Delete pipeline_templates"}
      >
        <p>Are you sure you wish to delete the {selectedItems.length} selected pipeline templates?</p>
      </CMFModal>
    </div>
  );
};

// Component TableView is a skeleton of a Table using AWS-UI React components.
export default UserPipelineTemplateTable;
