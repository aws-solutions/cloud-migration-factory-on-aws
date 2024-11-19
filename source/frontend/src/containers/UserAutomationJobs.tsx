/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ButtonDropdownProps, SpaceBetween, StatusIndicator } from "@cloudscape-design/components";

import AutomationJobView from "../components/AutomationJobView";
import { useAutomationJobs } from "../actions/AutomationJobsHook";
import { useMFWaves } from "../actions/WavesHook";
import ItemTable from "../components/ItemTable";
import AutomationTools from "../components/AutomationTools";
import ToolsAPI from "../api_clients/toolsApiClient";
import { userAutomationActionsMenuItems } from "../resources/main";
import { useAutomationScripts } from "../actions/AutomationScriptsHook";
import { useCredentialManager } from "../actions/CredentialManagerHook";
import { ClickEvent } from "../models/Events";
import { NotificationContext } from "../contexts/NotificationContext";
import { EntitySchema } from "../models/EntitySchema";
import { UserAccess } from "../models/UserAccess";
import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook";

type AutomationJobsParams = {
  schemas: Record<string, EntitySchema>;
  schemaIsLoading?: boolean;
  isReady?: boolean;
  userEntityAccess: UserAccess;
};
const AutomationJobs = (props: AutomationJobsParams) => {
  const { addNotification } = useContext(NotificationContext);
  let navigate = useNavigate();
  let params = useParams();
  //Data items for viewer and table.
  //Main table content hook. When duplicating just create a new hook and change the hook function at the end to populate table.
  const [{ isLoading: isLoadingMain, data: dataMain, error: errorMain }, { update: updateMain }] = useAutomationJobs();
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }] = useMFWaves();
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }] = useGetServers();
  const [{ isLoading: isLoadingScripts, data: dataScripts, error: errorScripts }] = useAutomationScripts();
  const [{ isLoading: isLoadingSecrets, data: dataSecrets, error: errorSecrets }] = useCredentialManager();

  const dataAll = {
    secret: { data: dataSecrets, isLoading: isLoadingSecrets, error: errorSecrets },
    script: { data: dataScripts, isLoading: isLoadingScripts, error: errorScripts },
    jobs: { data: dataMain, isLoading: isLoadingMain, error: errorMain },
    wave: { data: dataWaves, isLoading: isLoadingWaves, error: errorWaves },
    server: { data: dataServers, isLoading: isLoadingServers, error: errorServers },
    application: { data: dataApps, isLoading: isLoadingApps, error: errorApps },
  };

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [focusItem, setFocusItem] = useState<any>([]);
  const [filterJobsShowAll, setFilterJobsShowAll] = useState(false);

  //Add Job/Action state management.
  const [automationAction, setAutomationAction] = useState<string | undefined>(undefined);
  const [preformingAction, setPreformingAction] = useState(false);

  //Viewer pane state management.
  const [viewerCurrentTab, setViewerCurrentTab] = useState("details");
  const [action, setAction] = useState<string>("add");
  const [actions, setActions] = useState<ButtonDropdownProps.ItemOrGroup[]>([]);

  //Get base path from the URL, all actions will use this base path.
  const basePath = "/automation/jobs";
  //Key for main item displayed in table.
  const itemIDKey = "uuid";
  const schemaName = "job";

  async function handleRefreshClick() {
    await updateMain(filterJobsShowAll ? -1 : 30);
  }

  function handleResetScreen() {
    navigate({
      pathname: basePath,
    });

    setAction("View");
  }

  function handleItemSelectionChange(selection: Array<any>) {
    setSelectedItems(selection);

    //Reset URL to base table path.
    navigate({
      pathname: basePath,
    });
  }

  const ViewAutomationJob = (props: { schema: { [x: string]: any } }) => {
    if (selectedItems.length === 1) {
      return (
        <AutomationJobView
          item={selectedItems[0]}
          schema={props.schema["job"]}
          schemas={props.schema}
          dataAll={dataAll}
          handleTabChange={setViewerCurrentTab}
          selectedTab={viewerCurrentTab}
        />
      );
    } else {
      return null;
    }
  };

  async function handleActionsClick(e: ClickEvent) {
    let action = e.detail.id;

    setFocusItem(selectedItems);
    setAutomationAction(action);
    setAction("Action");
  }

  async function handleAction(actionData: any, actionId: number) {
    setPreformingAction(true);

    let newItem = Object.assign({}, actionData);
    let notificationId;

    let apiAction = props.schemas[automationAction!]?.actions?.filter((entry: { id: number }) => entry.id === actionId);

    if (apiAction?.length !== 1) {
      addNotification({
        type: "error",
        dismissible: true,
        header: "Perform wave action",
        content: `${props.schemas[automationAction!].friendly_name} action [${actionId}] not found in schema.`,
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
          type: "success",
          loading: true,
          dismissible: false,
          header: "Perform wave action",
          content: "Performing action - " + apiAction[0].name,
        });

        const apiTools = new ToolsAPI();
        const response = await apiTools.postTool(apiAction[0].apiPath, newItem);
        console.log(response);

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

        await updateMain(filterJobsShowAll ? -1 : 30);
      } catch (e: any) {
        await handleActionError(e, notificationId, apiAction);
      }
    }

    setPreformingAction(false);
  }

  async function handleActionError(e: any, notificationId: string | undefined, apiAction: any[]) {
    console.log(e);
    if ("response" in e) {
      if (e.response != null && typeof e.response === "object") {
        if ("data" in e.response) {
          addNotification({
            id: notificationId,
            type: "error",
            dismissible: true,
            header: "Perform wave action",
            content: apiAction[0].name + " action failed: " + e.response.data,
          });
        }
      } else {
        addNotification({
          id: notificationId,
          type: "error",
          dismissible: true,
          header: "Perform wave action",
          content: apiAction[0].name + " action failed: " + e.message,
        });
      }
    } else {
      addNotification({
        id: notificationId,
        type: "error",
        dismissible: true,
        header: "Perform wave action",
        content: apiAction[0].name + " action failed: Unknown error occured",
      });
    }
  }

  async function handleFilterDaysChange(flag: boolean | ((prevState: boolean) => boolean)) {
    setFilterJobsShowAll(flag);

    await updateMain(flag ? -1 : 30);
  }

  //Update actions button options on schema change.
  useEffect(() => {
    if (!props.schemaIsLoading && props.isReady) {
      setActions(userAutomationActionsMenuItems(props.schemas, props.userEntityAccess));
    }
  }, [props.schemas, props.userEntityAccess]);

  useEffect(() => {
    let selected = [];

    if (!isLoadingMain) {
      if (params.id) {
        //URL parameter present.
        let item = dataMain.filter((entry: { [x: string]: string | undefined }) => entry[itemIDKey] === params.id);

        selected.push(item[0]);
        handleItemSelectionChange(selected);
      }
    }
  }, [dataMain]);

  //Detect changes to main data table content and if an item was previously selected and in the viewer, refresh the item
  //content.
  useEffect(() => {
    let selected: any[] = [];

    if (!isLoadingMain) {
      if (selectedItems.length == 1) {
        //Refresh selected item.
        let item = dataMain.filter((entry: { [x: string]: any }) => entry[itemIDKey] === selectedItems[0][itemIDKey]);

        if (item.length === 1) {
          //Previous Item found in new data, reload into selected items.
          selected.push(item[0]);
          handleItemSelectionChange(selected);
        } else {
          //Item no longer available.
          handleItemSelectionChange(selected);
        }
      }
    }
  }, [dataMain]);

  function provideContent(currentAction: string) {
    if (props.schemaIsLoading || !props.isReady) {
      return <StatusIndicator type="loading">Loading schema...</StatusIndicator>;
    }

    if (currentAction === "Action") {
      return (
        <AutomationTools
          schema={props.schemas[automationAction!]}
          schemas={props.schemas}
          schemaName={schemaName}
          userAccess={props.userEntityAccess}
          performingAction={preformingAction}
          selectedItems={focusItem}
          handleAction={handleAction}
          handleCancel={handleResetScreen}
        />
      );
    } else {
      return (
        <SpaceBetween direction="vertical" size="xs">
          <ItemTable
            description={filterJobsShowAll ? "Displaying all jobs." : "Displaying only the last 30 days of jobs."}
            schema={props.schemas["job"]}
            schemaKeyAttribute={itemIDKey}
            schemaName={schemaName}
            dataAll={dataAll}
            items={dataMain}
            selectedItems={selectedItems}
            handleSelectionChange={handleItemSelectionChange}
            actionsButtonDisabled={false}
            selectionType={"single"}
            actionItems={actions}
            handleAction={handleActionsClick}
            isLoading={isLoadingMain}
            errorLoading={errorMain}
            handleRefreshClick={handleRefreshClick}
            userAccess={props.userEntityAccess}
            handleDaysFilterChange={handleFilterDaysChange}
          />
          <ViewAutomationJob schema={props.schemas} />
        </SpaceBetween>
      );
    }
  }

  return provideContent(action);
};

export default AutomationJobs;
