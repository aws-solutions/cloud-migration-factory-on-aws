/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useContext, useEffect, useState} from 'react';
import UserApiClient from "../api_clients/userApiClient";
import {useLocation, useNavigate, useParams} from "react-router-dom";
import ItemAmend from "../components/ItemAmend";
import {getChanges} from '../resources/main'
import {exportTable} from "../utils/xlsx-export";
import {SpaceBetween} from '@awsui/components-react';

import DatabaseView from '../components/DatabaseView';
import {useMFApps} from "../actions/ApplicationsHook";
import {useGetDatabases} from "../actions/DatabasesHook";
import {useGetServers} from "../actions/ServersHook";
import {useMFWaves} from "../actions/WavesHook";
import ItemTable from '../components/ItemTable';
import {apiActionErrorHandler, parsePUTResponseErrors} from "../resources/recordFunctions";
import {NotificationContext} from "../contexts/NotificationContext";
import {EntitySchema} from "../models/EntitySchema";
import {ToolsContext} from "../contexts/ToolsContext";
import {CMFModal} from "../components/Modal";

const ViewItem = (props: {
  schema: Record<string, EntitySchema>;
  selectedItems: any[];
  dataAll: any;
}) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState('details');

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
}

type UserDatabaseTableParams = {
  schemas: Record<string, EntitySchema>;
  userEntityAccess: any;
  schemaIsLoading?: boolean;
};
const UserDatabaseTable = ({schemas, userEntityAccess}: UserDatabaseTableParams) => {
  const {addNotification} = useContext(NotificationContext);
  const {setHelpPanelContentFromSchema} = useContext(ToolsContext);

  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();

  //Data items for viewer and table.
  const [{isLoading: isLoadingApps, data: dataApps, error: errorApps},] = useMFApps();
  const [{isLoading: isLoadingMain, data: dataMain, error: errorMain}, {update: updateMain}] = useGetDatabases();
  const [{isLoading: isLoadingServers, data: dataServers, error: errorServers},] = useGetServers();
  const [{isLoading: isLoadingWaves, data: dataWaves, error: errorWaves},] = useMFWaves();

  const dataAll = {
    application: {
      data: dataApps,
      isLoading: isLoadingApps,
      error: errorApps
    }, database: {
      data: dataMain,
      isLoading: isLoadingMain,
      error: errorMain
    }, server: {
      data: dataServers,
      isLoading: isLoadingServers,
      error: errorServers
    }, wave: {
      data: dataWaves,
      isLoading: isLoadingWaves,
      error: errorWaves
    }
  };

  //Layout state management.
  const [editingItem, setEditingItem] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<Array<any>>([]);
  const [focusItem, setFocusItem] = useState<any>([]);

  //Viewer pane state management.
  const [action, setAction] = useState('Add');

  //Get base path from the URL, all actions will use this base path.
  const basePath = location.pathname.split('/').length >= 2 ? '/' + location.pathname.split('/')[1] : '/';
  //Key for main item displayed in table.
  const itemIDKey = 'database_id';
  const schemaName = 'database';

  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = useState(false);


  function handleAddItem() {
    navigate({
      pathname: basePath + '/add'
    })
    setAction('Add')
    setFocusItem({});
    setEditingItem(true);
  }

  function handleDownloadItems() {
    if (selectedItems.length > 0) {
      // Download selected only.
      exportTable(selectedItems, "Databases", schemaName + 's')
    } else {
      //Download all.
      exportTable(dataServers, "Databases", schemaName + 's')
    }
  }

  function handleEditItem(selection = null) {
    if (selectedItems.length === 1) {
      navigate({
        pathname: basePath + '/edit/' + selectedItems[0][itemIDKey]
      })
      setAction('Edit')
      setFocusItem(selectedItems[0]);
      setEditingItem(true);
    } else if (selection) {
      navigate({
        pathname: basePath + '/edit/' + selection[itemIDKey]
      })
      setAction('Edit');
      setFocusItem(selection);
      setEditingItem(true);
    }

  }

  function handleResetScreen() {
    navigate({
      pathname: basePath
    })
    setEditingItem(false);
  }

  function handleItemSelectionChange(selection: Array<any>) {

    setSelectedItems(selection);
    if (selection.length === 1) {

      //ATTN: Need to pull in Waves or other data here.
      //updateApps(selection[0].app_id);

    }
    //Reset URL to base table path.
    navigate({
      pathname: basePath
    })

  }

  async function handleEditSave(editedItem: any): Promise<void> {

    let newItem = Object.assign({}, editedItem);
    let item_id = newItem[schemaName + '_id'];
    let item_name = newItem[schemaName + '_name'];
    const apiUser = new UserApiClient();

    newItem = getChanges(newItem, dataMain, itemIDKey);
    if (!newItem) {
      // no changes to original record.
      addNotification({
        type: 'warning',
        dismissible: true,
        header: "Save " + schemaName,
        content: "No updates to save."
      })
      return;
    }
    delete newItem[schemaName + '_id'];
    let resultEdit = await apiUser.putItem(item_id, newItem, schemaName);

    if (resultEdit['errors']) {
      console.debug("PUT " + schemaName + " errors");
      console.debug(resultEdit['errors']);
      let errorsReturned = parsePUTResponseErrors(resultEdit['errors']).join(',');
      addNotification({
        type: 'error',
        dismissible: true,
        header: "Update " + schemaName,
        content: (errorsReturned)
      })
    } else {
      addNotification({
        type: 'success',
        dismissible: true,
        header: "Update " + schemaName,
        content: item_name + " updated successfully.",
      })
      updateMain();
      handleResetScreen();

      //This is needed to ensure the item in selectItems reflects new updates
      setSelectedItems([]);
      setFocusItem({});
    }
  }

  async function handleNewSave(editedItem: any) {
    let newItem = Object.assign({}, editedItem);
    const apiUser = new UserApiClient();

    delete newItem[schemaName + '_id'];
    let resultAdd = await apiUser.postItem(newItem, schemaName);

    if (resultAdd['errors']) {
      console.debug("PUT " + schemaName + " errors");
      console.debug(resultAdd['errors']);
      let errorsReturned = parsePUTResponseErrors(resultAdd['errors']).join(',');
      addNotification({
        type: 'error',
        dismissible: true,
        header: "Add " + schemaName,
        content: (errorsReturned)
      })
      return false;
    } else {
      addNotification({
        type: 'success',
        dismissible: true,
        header: "Add " + schemaName,
        content: newItem[schemaName + '_name'] + " added successfully.",
      })
      updateMain();
      handleResetScreen();
    }
  }

  async function handleSave(editItem: any, action: string) {

    let newItem = Object.assign({}, editItem);
    try {
      if (action === 'Edit') {
        await handleEditSave(newItem);
      } else {
        await handleNewSave(newItem);
      }

    } catch (e: any) {
      apiActionErrorHandler(action, schemaName, e, addNotification);
    }
  }

  async function handleRefreshClick() {
    await updateMain();
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
          type: 'success',
          loading: true,
          dismissible: false,
          header: "Deleting selected " + schemaName + "s..."
        });
      }

      for (let item in selectedItems) {
        currentItem = item;
        await apiUser.deleteDatabase(selectedItems[item][schemaName + '_id']);
        //Combine notifications into a single message if multi selected used, to save user dismiss clicks.
        if (selectedItems.length > 1) {
          multiReturnMessage.push(selectedItems[item][schemaName + '_name']);
        } else {
          addNotification({
            type: 'success',
            dismissible: true,
            header: schemaName + ' deleted successfully',
            content: selectedItems[item][schemaName + '_name'] + ' was deleted.'
          })
        }

      }

      //Create notification where multi select was used.
      if (selectedItems.length > 1) {
        addNotification({
          id: notificationId,
          type: 'success',
          dismissible: true,
          header: schemaName + ' deleted successfully',
          content: multiReturnMessage.join(", ") + ' were deleted.'
        })
      }


      //Unselect applications marked for deletion to clear apps.
      setSelectedItems([]);
      await updateMain();

    } catch (e: any) {
      console.log(e);
      addNotification({
        type: 'error',
        dismissible: true,
        header: schemaName + ' deletion failed',
        content: selectedItems[currentItem][schemaName + '_name'] + ' failed to delete.'
      })
    }
  }

  function displayItemsViewScreen() {
    return <SpaceBetween direction="vertical" size="xs">
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
      />
      <ViewItem
        schema={schemas}
        selectedItems={selectedItems}
        dataAll={dataAll}
      />
    </SpaceBetween>
  }

  function displayItemsScreen() {
    if (editingItem) {
      return <ItemAmend action={action} schemaName={schemaName} schemas={schemas}
                        userAccess={userEntityAccess} item={focusItem} handleSave={handleSave}
                        handleCancel={handleResetScreen}/>;
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
        //Check if URL contains edit path and switch to amend component.
        if (location?.pathname.match('/edit/')) {
          handleEditItem(item[0]);
        }
      } else if (location?.pathname.match('/add')) {
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
        header={'Delete databases'}
      >
        <p>Are you sure you wish to delete the {selectedItems.length} selected databases?</p>
      </CMFModal>

    </div>
  );
};

// Component TableView is a skeleton of a Table using AWS-UI React components.
export default UserDatabaseTable;
