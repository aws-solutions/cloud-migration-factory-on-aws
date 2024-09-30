/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useEffect, useState } from "react";
import UserApiClient from "../api_clients/userApiClient";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import ItemAmend from "../components/ItemAmend";
import { getChanges } from "../resources/main";
import { exportTable } from "../utils/xlsx-export";
import { SpaceBetween } from "@cloudscape-design/components";

import ServerView from "../components/ServerView";
import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import ItemTable from "../components/ItemTable";
import { apiActionErrorHandler, parsePUTResponseErrors } from "../resources/recordFunctions";
import { NotificationContext } from "../contexts/NotificationContext";
import { EntitySchema } from "../models/EntitySchema";
import { ToolsContext } from "../contexts/ToolsContext";
import { CMFModal } from "../components/Modal";

type ViewServerParams = {
  selectedItems: any[];
  dataAll: { application: { data: any[] } };
  isLoadingApps?: boolean;
  schemas: Record<string, EntitySchema>;
  errorApps: any;
};
const ViewServer = (props: ViewServerParams) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState<string>("details");

  if (props.selectedItems.length === 1) {
    const currentServerApplication = props.dataAll.application.data.filter(function (entry: any) {
      return entry.app_id === props.selectedItems[0].app_id;
    });

    const app = { items: currentServerApplication, isLoading: props.isLoadingApps, error: props.errorApps };
    return (
      <ServerView
        server={props.selectedItems[0]}
        app={app}
        handleTabChange={setViewerCurrentTab}
        dataAll={props.dataAll}
        selectedTab={viewerCurrentTab}
        schemas={props.schemas}
      />
    );
  } else {
    return null;
  }
};

type UserServerTableParams = {
  schemas: Record<string, EntitySchema>;
  userEntityAccess: any;
  schemaIsLoading?: boolean;
};
const UserServerTable = ({ schemas, userEntityAccess }: UserServerTableParams) => {
  const { addNotification } = useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = useContext(ToolsContext);
  let location = useLocation();
  let navigate = useNavigate();
  let params = useParams();

  //Data items for viewer and table.
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }, { update: updateServers }] =
    useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }] = useMFWaves();

  const dataAll = {
    application: {
      data: dataApps,
      isLoading: isLoadingApps,
      error: errorApps,
    },
    server: {
      data: dataServers,
      isLoading: isLoadingServers,
      error: errorServers,
    },
    wave: {
      data: dataWaves,
      isLoading: isLoadingWaves,
      error: errorWaves,
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
  const itemIDKey = "server_id";
  const schemaName = "server";

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
      exportTable(selectedItems, "Servers", "servers");
    } else {
      //Download all.
      exportTable(dataServers, "Servers", "servers");
    }
  }

  function handleEditItem(selection = null) {
    if (selectedItems.length === 1) {
      navigate({
        pathname: basePath + "/edit/" + selectedItems[0][itemIDKey],
      });
      setAction("Edit");
      setFocusItem(selectedItems[0]);
      setEditingItem(true);
    } else if (selection) {
      // ATTN: is this else branch reachable or dead code?
      navigate({
        pathname: basePath + "/edit/" + selection[itemIDKey],
      });
      setAction("Edit");
      setFocusItem(selection);
      setEditingItem(true);
    }
  }

  function handleResetScreen() {
    setEditingItem(false);
    navigate({
      pathname: basePath,
    });
  }

  function handleItemSelectionChange(selection: Array<any>) {
    setSelectedItems(selection);
    if (selection.length === 1) {
      //TO-DO Need to pull in Waves or other data here.
      //updateApps(selection[0].app_id);
    }
    //Reset URL to base table path.
    navigate({
      pathname: basePath,
    });
  }

  async function handleSave(editItem: any, action: string): Promise<void> {
    let newItem = Object.assign({}, editItem);
    let result;
    try {
      const apiUser = new UserApiClient();
      const server_name = newItem.server_name;
      if (action === "Edit") {
        let server_id = newItem.server_id;
        newItem = getChanges(newItem, dataServers, "server_id");
        if (!newItem) {
          // no changes to original record.
          addNotification({
            type: "warning",
            dismissible: true,
            header: "Save " + schemaName,
            content: "No updates to save.",
          });
          return;
        }
        result = await apiUser.putItem(server_id, newItem, "server");
      } else {
        delete newItem.server_id;
        result = await apiUser.postItem(newItem, "server");
      }

      if (result["errors"]) {
        let errorsReturned = parsePUTResponseErrors(result["errors"]).join(",");
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
          header: `${action} ${schemaName}`,
          content: server_name + " saved successfully.",
        });
        await updateServers();
        handleResetScreen();

        //This is needed to ensure the item in selectItems reflects new updates
        setSelectedItems([]);
        setFocusItem({});
      }
    } catch (e: any) {
      apiActionErrorHandler(action, schemaName, e, addNotification);
    }
  }

  async function handleRefreshClick() {
    await updateServers();
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
          header: "Deleting selected servers...",
        });
      }
      for (let item in selectedItems) {
        currentItem = item;
        await apiUser.deleteServer(selectedItems[item].server_id);
        //Combine notifications into a single message if multi selected used, to save user dismiss clicks.
        if (selectedItems.length > 1) {
          multiReturnMessage.push(selectedItems[item].server_name);
        } else {
          addNotification({
            type: "success",
            dismissible: true,
            header: "Server deleted successfully",
            content: selectedItems[item].server_name + " was deleted.",
          });
        }
      }

      //Create notification where multi select was used.
      if (selectedItems.length > 1) {
        addNotification({
          id: notificationId,
          type: "success",
          dismissible: true,
          header: "Servers deleted successfully",
          content: multiReturnMessage.join(", ") + " were deleted.",
        });
      }

      //Unselect applications marked for deletion to clear apps.
      setSelectedItems([]);
      await updateServers();
    } catch (e: any) {
      console.error(e);
      addNotification({
        type: "error",
        dismissible: true,
        header: "Server deletion failed",
        content: selectedItems[currentItem].server_name + " failed to delete.",
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
          items={dataServers}
          selectedItems={selectedItems}
          handleSelectionChange={handleItemSelectionChange}
          isLoading={isLoadingServers}
          errorLoading={errorServers}
          handleRefreshClick={handleRefreshClick}
          handleAddItem={handleAddItem}
          handleDeleteItem={async function () {
            setDeleteConfirmationModalVisible(true);
          }}
          handleEditItem={handleEditItem}
          handleDownloadItems={handleDownloadItems}
          userAccess={userEntityAccess}
        />
        <ViewServer
          schemas={schemas}
          dataAll={dataAll}
          selectedItems={selectedItems}
          isLoadingApps={isLoadingApps}
          errorApps={errorApps}
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

    if (!isLoadingServers) {
      let item = dataServers.filter(function (entry: any) {
        return entry[itemIDKey] === params.id;
      });

      if (item.length === 1) {
        selected.push(item[0]);
        handleItemSelectionChange(selected);
        //Check if URL contains edit path and switch to amend component.
        if (location.pathname && location.pathname.match("/edit/")) {
          handleEditItem(item[0]);
        }
      } else if (location.pathname && location.pathname.match("/add")) {
        //Add url used, redirect to add screen.
        handleAddItem();
      }
    }
  }, [dataServers]);

  //Update help tools panel
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
        header={"Delete servers"}
      >
        <p>Are you sure you wish to delete the {selectedItems.length} selected servers?</p>
      </CMFModal>
    </div>
  );
};
export default UserServerTable;
