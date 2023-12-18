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
import {Box, Button, Modal, SpaceBetween} from '@awsui/components-react';


import ApplicationView from '../components/ApplicationView'
import {useMFApps} from "../actions/ApplicationsHook";
import {useGetServers} from "../actions/ServersHook";
import {useMFWaves} from "../actions/WavesHook";
import ItemTable from '../components/ItemTable';
import {apiActionErrorHandler, parsePUTResponseErrors} from "../resources/recordFunctions";
import {NotificationContext} from "../contexts/NotificationContext";
import {EntitySchema} from "../models/EntitySchema";
import {ToolsContext} from "../contexts/ToolsContext";

type ViewApplicationParams = {
  selectedItems: any[];
  dataWaves: any;
  dataAll: any;
  dataServers: any;
  isLoadingServers: any;
  errorServers: any;
  schemas: Record<string, EntitySchema>
};
const ViewApplication = (props: ViewApplicationParams) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState('details');

  function getCurrentApplicationWave(selectedItems: any[], dataWaves: any[]) {

    if (selectedItems.length === 1) {
      let waves = dataWaves.filter(function (entry) {
        return entry.wave_id === selectedItems[0].wave_id;
      });

      if (waves.length === 1) {
        return waves[0];
      } else {
        return {};
      }
    }

  }

  if (props.selectedItems.length === 1) {
    return (
      <ApplicationView
        schemas={props.schemas}
        app={props.selectedItems[0]}
        wave={getCurrentApplicationWave(props.selectedItems, props.dataWaves)}
        dataAll={props.dataAll}
        servers={{
          items: props.dataServers,
          isLoading: props.isLoadingServers,
          error: props.errorServers
        }}
        handleTabChange={setViewerCurrentTab}
        selectedTab={viewerCurrentTab}
      />
    );
  } else {
    return null;
  }
}

type AppTableParams = {
  schemas: Record<string, EntitySchema>;
  userEntityAccess: any;
  schemaIsLoading?: boolean;
};
const AppTable = ({schemas, userEntityAccess}: AppTableParams) => {

  const {addNotification} = useContext(NotificationContext);
  const {setHelpPanelContentFromSchema} = useContext(ToolsContext);


  const location = useLocation();
  const navigate = useNavigate();
  const urlParams = useParams();
  //Data items for viewer and table.
  //Main table content hook. When duplicating just create a new hook and change the hook function at the end to populate table.
  const [{isLoading: isLoadingMain, data: dataMain, error: errorMain}, {update: updateMain}] = useMFApps();
  const [{
    isLoading: isLoadingServers,
    data: dataServers,
    error: errorServers
  }, {update: updateServers}] = useGetServers();
  const [{isLoading: isLoadingWaves, data: dataWaves, error: errorWaves},] = useMFWaves();

  const dataAll = {
    application: {data: dataMain, isLoading: isLoadingMain, error: errorMain},
    server: {data: dataServers, isLoading: isLoadingServers, error: errorServers},
    wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}
  };

  //Layout state management.
  const [editingItem, setEditingItem] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [focusItem, setFocusItem] = useState<any>([]);

  //Viewer pane state management.

  const [action, setAction] = useState('Add');

  //Get base path from the URL, all actions will use this base path.
  const basePath = location.pathname.split('/').length >= 2 ? '/' + location.pathname.split('/')[1] : '/';
  //Key for main item displayed in table.
  const itemIDKey = 'app_id';
  const schemaName = 'application';

  //Modals
  const [modalVisible, setModalVisible] = useState(false);

  async function handleRefreshClick(e: any) {
    e.preventDefault();
    await updateMain();
  }

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
      exportTable(selectedItems, "Applications", "applications")
    } else {
      //Download all.
      exportTable(dataMain, "Applications", "applications")
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

      updateServers(selection[0][itemIDKey]);

    }
    //Reset URL to base table path.
    navigate({
      pathname: basePath
    })

  }

  async function handleEditSave(editedItem: any): Promise<void> {

    let newApp = Object.assign({}, editedItem);
    let app_id = newApp.app_id;
    let app_name = newApp.app_name;
    const apiUser = new UserApiClient();

    newApp = getChanges(newApp, dataMain, itemIDKey);
    if (!newApp) {
      // no changes to original record.
      addNotification({
        type: 'warning',
        dismissible: true,
        header: "Save " + schemaName,
        content: "No updates to save."
      })
      return;
    }
    delete newApp.app_id;
    let resultEdit = await apiUser.putItem(app_id, newApp, schemaName);

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
        content: app_name + " updated successfully.",
      })
      updateMain();
      handleResetScreen();

      //This is needed to ensure the item in selectItems reflects new updates
      setSelectedItems([]);
      setFocusItem({});
    }
  }

  async function handleNewSave(editedItem: any) {

    let newApp = Object.assign({}, editedItem);
    const apiUser = new UserApiClient();

    delete newApp.app_id;
    let resultAdd = await apiUser.postItem(newApp, schemaName);

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
    } else {
      addNotification({
        type: 'success',
        dismissible: true,
        header: "Add " + schemaName,
        content: newApp.app_name + " added successfully.",
      })
      updateMain();
      handleResetScreen();
    }
  }


  async function handleSave(editedItem: any, action: string) {

    try {
      if (action === 'Edit') {
        await handleEditSave(editedItem);
      } else {
        await handleNewSave(editedItem);
      }
    } catch (e: any) {
      apiActionErrorHandler(action, schemaName, e, addNotification);
    }

  }

  async function handleDeleteItemClick() {
    setModalVisible(true);
  }

  async function handleDeleteItem() {
    setModalVisible(false);

    let currentApp: any = 0;
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
        currentApp = item;
        await apiUser.deleteApp(selectedItems[item][itemIDKey]);
        //Combine notifications into a single message if multi selected used, to save user dismiss clicks.
        if (selectedItems.length > 1) {
          multiReturnMessage.push(selectedItems[item].app_name);
        } else {
          addNotification({
            type: 'success',
            dismissible: true,
            header: 'Application deleted successfully',
            content: selectedItems[item].app_name + ' was deleted.'
          })
        }

      }

      //Create notification where multi select was used.
      if (selectedItems.length > 1) {
        addNotification({
          id: notificationId,
          type: 'success',
          dismissible: true,
          header: 'Applications deleted successfully',
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
        header: 'Application deletion failed',
        content: selectedItems[currentApp].app_name + ' failed to delete.'
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
        handleDeleteItem={handleDeleteItemClick}
        handleEditItem={handleEditItem}
        handleDownloadItems={handleDownloadItems}
        userAccess={userEntityAccess}
      />
      <ViewApplication
        schemas={schemas}
        dataAll={dataAll}
        dataWaves={dataWaves}
        dataServers={dataServers}
        selectedItems={selectedItems}
        isLoadingServers={isLoadingServers}
        errorServers={errorServers}
      />
    </SpaceBetween>
  }

  function displayItemsScreen() {
    if (editingItem) {
      return <ItemAmend
        action={action}
        schemaName={schemaName}
        schemas={schemas}
        userAccess={userEntityAccess}
        item={focusItem}
        handleSave={handleSave}
        handleCancel={handleResetScreen}/>;
    } else {
      return displayItemsViewScreen();
    }
  }

  useEffect(() => {

    if (!isLoadingMain) {

      const item = dataMain.find((entry: Record<string, any>) => {
        return entry[itemIDKey] === urlParams.id;
      });

      if (item) {
        handleItemSelectionChange([item]);
        //Check if URL contains edit path and switch to amend component.
        if (location?.pathname.match('/edit/')) {
          handleEditItem(item);
        }
      } else if (location?.pathname.match('/add')) {
        //Add url used, redirect to add screen.
        handleAddItem();
      }
    }

  }, [dataMain]);

  //Update help tools panel
  useEffect(() => {
    setHelpPanelContentFromSchema(schemas, schemaName);
  }, [schemas]);

  return (
    <div>
      {displayItemsScreen()}
      {modalVisible ?
        <Modal
          visible={true}
          closeAriaLabel="Close modal"
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button variant="link" onClick={() => setModalVisible(false)}>Cancel</Button>
                <Button variant="primary" onClick={handleDeleteItem}>Ok</Button>
              </SpaceBetween>
            </Box>
          }
          header="Delete applications">
          {selectedItems.length === 1 ?
            <p>Are you sure you wish to delete the selected application?</p> :
            <p>Are you sure you wish to delete the {selectedItems.length} selected applications?</p>
          }
        </Modal> :
        <></>}
    </div>
  );
};

export default AppTable;
