/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { SpaceBetween } from "@cloudscape-design/components";
import { useContext, useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import UserApiClient from "../api_clients/userApiClient";
import ItemAmend from "../components/ItemAmend";
import { getChanges } from "../resources/main";
import { exportTable } from "../utils/xlsx-export";

import { useGetItems } from "../actions/ItemsHook";
import ToolsApiClient from "../api_clients/toolsApiClient";
import ItemTable from "../components/ItemTable";
import { CMFModal } from "../components/Modal";
import WPMJobView from "../components/WPMJobView";
import { NotificationContext } from "../contexts/NotificationContext";
import { ToolsContext } from "../contexts/ToolsContext";
import { EntitySchema, UserAccess, WPMJob, Wave, MoveGroup } from "../models";
import { apiActionErrorHandler, parsePUTResponseErrors, UNEXPECTED_ERROR } from "../resources/recordFunctions";
import { Schemas } from "../utils/Constants";
import { useMFWaves } from "../actions/WavesHook";

type ViewWPMJobParams = {
  selectedItems: WPMJob[];
  dataAll: { wpm_job: { data: WPMJob[] }; wave: { data: Wave[] }; move_group: { data: MoveGroup[] } };
  schemas: Record<string, EntitySchema>;
};
const ViewWPMJob = (props: ViewWPMJobParams) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState<string>("details");

  if (props.selectedItems.length === 1) {
    return (
      <WPMJobView
        wpm_job={props.selectedItems[0]}
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

type UserWPMJobTableParams = {
  schemas: Record<string, EntitySchema>;
  userEntityAccess: UserAccess;
};
const UserWPMJobTable = ({ schemas, userEntityAccess }: UserWPMJobTableParams) => {
  const { addNotification } = useContext(NotificationContext);
  const { setHelpPanelContentFromSchema } = useContext(ToolsContext);
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  //Data items for viewer and table.
  const [{ isLoading: isLoadingWPMJobs, data: dataWPMJobs, error: errorWPMJobs }, { update: updateItems }] =
    useGetItems(Schemas.WPMJob.name);
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, { update: updateWaves }] =
    useMFWaves<Wave>();
  const [
    { isLoading: isLoadingMoveGroups, data: dataMoveGroups, error: errorMoveGroups },
    { update: updateMoveGroups },
  ] = useGetItems<MoveGroup>(Schemas.MoveGroup.name);

  const dataAll = {
    wpm_job: {
      data: dataWPMJobs,
      isLoading: isLoadingWPMJobs,
      error: errorWPMJobs,
    },
    wave: {
      data: dataWaves,
      isLoading: isLoadingWaves,
      error: errorWaves,
    },
    move_group: {
      data: dataMoveGroups,
      isLoading: isLoadingMoveGroups,
      error: errorMoveGroups,
    },
  };

  //Layout state management.
  const [editingItem, setEditingItem] = useState(location.pathname.includes("edit"));

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<Array<WPMJob>>([]);
  const [focusItem, setFocusItem] = useState<WPMJob>();

  //Viewer pane state management.
  const [action, setAction] = useState<string>("Add");

  //Get base path from the URL, all actions will use this base path.
  const basePath = "/wpm_jobs";

  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = useState(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  function handleAddItem() {
    navigate({
      pathname: basePath + "/add",
    });
    setAction("Add");
    setFocusItem(undefined);
    setEditingItem(true);
  }

  function handleDownloadItems() {
    // Download selected only if any item selected, otherwise all
    exportTable(selectedItems.length > 0 ? selectedItems : dataWPMJobs, "WPMJobs", "wpm_jobs");
  }

  function handleEditItem(selection = null) {
    if (selectedItems.length === 1) {
      navigate({
        pathname: basePath + "/edit/" + selectedItems[0][Schemas.WPMJob.keyAttribute],
      });
      setAction("Edit");
      setFocusItem(selectedItems[0]);
      setEditingItem(true);
    } else if (selection) {
      // ATTN: is this else branch reachable or dead code?
      navigate({
        pathname: basePath + "/edit/" + selection[Schemas.WPMJob.keyAttribute],
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

  function handleItemSelectionChange(selection: Array<WPMJob>) {
    setSelectedItems(selection);
    if (selection.length === 1) {
      // Update waves and move groups when a WPM job is selected
      updateWaves(Schemas.Wave.name);
      updateMoveGroups(Schemas.MoveGroup.name);
    }
    //Reset URL to base table path.
    navigate({
      pathname: basePath,
    });
  }

  async function handleSave(editItem: WPMJob, action: string): Promise<void> {
    let newItem = Object.assign({}, editItem);
    let result;
    try {
      const apiUser = new UserApiClient();
      const wpm_job_name = newItem.wpm_job_name;
      if (action === "Edit") {
        const wpm_job_id = newItem.wpm_job_id;
        newItem = getChanges(newItem, dataWPMJobs, Schemas.WPMJob.keyAttribute);
        if (!newItem || !wpm_job_id) {
          // no changes to original record.
          addNotification({
            type: "warning",
            dismissible: true,
            header: "Save " + Schemas.WPMJob.friendlyName,
            content: "No updates to save.",
          });
          return;
        }
        result = await apiUser.putItem(wpm_job_id, newItem, Schemas.WPMJob.name);
      } else {
        delete newItem.wpm_job_id;
        result = await apiUser.postItem(newItem, Schemas.WPMJob.name);
      }

      if (result["errors"]) {
        const errorsReturned = parsePUTResponseErrors(result["errors"]).join(",");
        addNotification({
          type: "error",
          dismissible: true,
          header: `${action} ${Schemas.WPMJob.friendlyName}`,
          content: errorsReturned,
        });
      } else {
        addNotification({
          type: "success",
          dismissible: true,
          header: `${action} ${Schemas.WPMJob.friendlyName}`,
          content: wpm_job_name + " saved successfully.",
        });
        await updateItems(Schemas.WPMJob.name);
        handleResetScreen();

        //This is needed to ensure the item in selectItems reflects new updates
        setSelectedItems([]);
        setFocusItem(undefined);
      }
    } catch (e) {
      apiActionErrorHandler(action, Schemas.WPMJob.name, e, addNotification);
    }
  }

  async function handleRefreshClick() {
    await updateItems(Schemas.WPMJob.name);
    await updateWaves(Schemas.Wave.name);
    await updateMoveGroups(Schemas.MoveGroup.name);
  }

  async function handleDeleteItem() {
    setDeleteConfirmationModalVisible(false);

    let notificationId;

    const currentSelectedItems = selectedItems;
    setIsDeleting(true);
    // Clear selected items so as to disable Edit/Edit buttons during deletion
    setSelectedItems([]);
    try {
      const apiTools = new ToolsApiClient();

      notificationId = addNotification({
        loading: true,
        dismissible: false,
        header: `Deleting ${Schemas.WPMJob.friendlyName}`,
      });

      await apiTools.cleanupEntities(
        "wpm_job",
        selectedItems.map((item) => item.wpm_job_id).filter((x): x is string => !!x)
      );

      //Create notification where multi select was used.
      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: `Delete ${Schemas.WPMJob.friendlyName}`,
        content: `${selectedItems.map((item) => item.wpm_job_name).join(", ")} ${selectedItems.length > 1 ? "were" : "was"} deleted.`,
      });

      await updateItems(Schemas.WPMJob.name);
    } catch (e) {
      console.error(e);
      // Revert selected items on error
      setSelectedItems(currentSelectedItems);
      addNotification({
        id: notificationId,
        type: "error",
        dismissible: true,
        header: `Delete ${Schemas.WPMJob.friendlyName}`,
        content: UNEXPECTED_ERROR,
      });
    } finally {
      setIsDeleting(false);
    }
  }

  function displayItemsViewScreen() {
    return (
      <SpaceBetween direction="vertical" size="xs">
        <ItemTable
          schema={schemas[Schemas.WPMJob.name]}
          schemaKeyAttribute={Schemas.WPMJob.keyAttribute}
          schemaName={Schemas.WPMJob.name}
          dataAll={dataAll}
          items={dataWPMJobs}
          selectedItems={selectedItems}
          handleSelectionChange={handleItemSelectionChange}
          isLoading={isLoadingWPMJobs || isDeleting}
          errorLoading={errorWPMJobs}
          handleRefreshClick={handleRefreshClick}
          handleAddItem={handleAddItem}
          handleDeleteItem={async function () {
            setDeleteConfirmationModalVisible(true);
          }}
          handleEditItem={handleEditItem}
          handleDownloadItems={handleDownloadItems}
          userAccess={userEntityAccess}
        />
        <ViewWPMJob schemas={schemas} dataAll={dataAll} selectedItems={selectedItems} />
      </SpaceBetween>
    );
  }

  function displayItemsScreen() {
    if (editingItem) {
      return (
        <ItemAmend
          action={action}
          schemaName={Schemas.WPMJob.name}
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
    const selected = [];

    if (!isLoadingWPMJobs) {
      const item = dataWPMJobs.filter(function (entry: WPMJob) {
        return entry[Schemas.WPMJob.keyAttribute] === params.id;
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
    // TODO: Will fix this when working on WPM-563
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataWPMJobs]);

  //Update help tools panel
  useEffect(() => {
    setHelpPanelContentFromSchema(schemas, Schemas.WPMJob.name);
  }, [schemas, setHelpPanelContentFromSchema]);

  return (
    <div>
      {displayItemsScreen()}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={`Delete ${Schemas.WPMJob.friendlyName}`}
      >
        <p>
          Are you sure you wish to delete the {selectedItems.length} selected WPM
          {selectedItems.length > 1 ? " Jobs" : " Job"}?
        </p>
      </CMFModal>
    </div>
  );
};

export default UserWPMJobTable;
