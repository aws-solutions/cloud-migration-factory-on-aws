/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import User from "../actions/user";
import {useLocation, useNavigate, useParams} from "react-router-dom";

import { Auth } from "@aws-amplify/auth";
import ItemAmend from "../components/ItemAmend";
import {
  capitalize,
  exportTable,
  getChanges
} from '../resources/main.js'

import {
  SpaceBetween,
  StatusIndicator
} from '@awsui/components-react';

import ServerView from '../components/ServerView.jsx';
import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook.js";
import { useMFWaves } from "../actions/WavesHook.js";
import ItemTable from '../components/ItemTable.jsx';
import { useModal } from '../actions/Modal.js';
import {parsePUTResponseErrors} from "../resources/recordFunctions";

const ViewServer = (props) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState('details');

  async function handleViewerTabChange(tabSelected)
  {
    setViewerCurrentTab(tabSelected);
  }

  function getCurrentServerApplication() {

    if (props.selectedItems.length === 1) {
      let apps = props.dataAll.application.data.filter(function (entry) {
        return entry.app_id === props.selectedItems[0].app_id;
      });

      if ( apps.length > 0){
        return apps;
      } else {
        return [];
      }
    }
  }

  if (props.selectedItems.length === 1) {

    return (
      <ServerView {...props}
                  server={props.selectedItems[0]}
                  app={{items: getCurrentServerApplication(), isLoading: props.isLoadingApps, error: props.errorApps}}
                  handleTabChange={handleViewerTabChange}
                  dataAll={props.dataAll}
                  selectedTab={viewerCurrentTab}/>
    );
  } else {
    return null;
  }
}

const UserServerTable = (props) => {
  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();

  //Data items for viewer and table.
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }, ] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }, { update: updateServers }] = useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, ] = useMFWaves();

  const dataAll = {application: {data: dataApps, isLoading: isLoadingApps, error: errorApps}, server: {data: dataServers, isLoading: isLoadingServers, error: errorServers}, wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}};

  //Layout state management.
  const [editingItem, setEditingItem] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState([]);
  const [focusItem, setFocusItem] = useState([]);

  //Viewer pane state management.
  const [action, setAction] = useState(['Add']);

  //Get base path from the URL, all actions will use this base path.
  const basePath = location.pathname.split('/').length >= 2 ? '/' + location.pathname.split('/')[1] : '/';

  //Key for main item displayed in table.
  const itemIDKey = 'server_id';
  const schemaName = 'server';

  const { show: showDeleteConfirmaton, hide: hideDeleteConfirmaton, RenderModal: DeleteModal } = useModal()

  function handleNotification(notification)
  {
    return props.updateNotification('add', notification)
  }

  function handleAddItem()
  {
    navigate({
      pathname: basePath + '/add'
    })
    setAction('Add')
    setFocusItem({});
    setEditingItem(true);

  }

  function handleDownloadItems()
  {
    if (selectedItems.length > 0 ) {
      // Download selected only.
      exportTable(selectedItems, "Servers", "servers")
    } else {
      //Download all.
      exportTable(dataServers, "Servers", "servers")
    }
  }

  function handleEditItem(selection = null)
  {
    if ( selectedItems.length === 1) {
      navigate({
        pathname: basePath + '/edit/' + selectedItems[0][itemIDKey]
      })
      setAction('Edit')
      setFocusItem(selectedItems[0]);
      setEditingItem(true);
    } else if ( selection ) {
      navigate({
        pathname: basePath + '/edit/' + selection[itemIDKey]
      })
      setAction('Edit');
      setFocusItem(selection);
      setEditingItem(true);
    }

  }

  function handleResetScreen()
  {
    navigate({
      pathname: basePath
    })
    setEditingItem(false);
  }

  function handleItemSelectionChange(selection) {

    setSelectedItems(selection);
    if (selection.length === 1) {

      //TO-DO Need to pull in Waves or other data here.
      //updateApps(selection[0].app_id);

    }
    //Reset URL to base table path.
    navigate({
      pathname: basePath
    })

  }

  async function handleSave(editItem, action) {

    let newItem = Object.assign({}, editItem);
    try {
      if (action === 'Edit') {
        let server_id = newItem.server_id;
        let server_ref = newItem.server_name;

        const session = await Auth.currentSession();
        const apiUser = new User(session);
        newItem = getChanges(newItem, dataServers, "server_id");
        if(!newItem){
          // no changes to original record.
          handleNotification({
            type: 'warning',
            dismissible: true,
            header: "Save " + schemaName,
            content: "No updates to save."
          });
          return false;
        }
        const resultEdit = await apiUser.putItem(server_id, newItem, 'server');

        if (resultEdit['errors']) {
          console.debug("PUT " + schemaName + " errors");
          console.debug(resultEdit['errors']);
          let errorsReturned = parsePUTResponseErrors(resultEdit['errors']);
          handleNotification({
            type: 'error',
            dismissible: true,
            header: "Update " + schemaName,
            content: (errorsReturned)
          });
        } else {
          handleNotification({
            type: 'success',
            dismissible: true,
            header: "Update " + schemaName,
            content: server_ref + " updated successfully.",
          });
          updateServers();
          handleResetScreen();

          //This is needed to ensure the item in selectItems reflects new updates
          setSelectedItems([]);
          setFocusItem({});
        }
      }
      else {

        const session = await Auth.currentSession();
        const apiUser = new User(session);
        delete newItem.server_id;
        const resultAdd = await apiUser.postItem(newItem, 'server');

        if (resultAdd['errors']) {
          console.debug("PUT " + schemaName + " errors");
          console.debug(resultAdd['errors']);
          let errorsReturned = parsePUTResponseErrors(resultAdd['errors']);
          handleNotification({
            type: 'error',
            dismissible: true,
            header: "Add " + schemaName,
            content: (errorsReturned)
          });
          return false;
        } else {
          handleNotification({
            type: 'success',
            dismissible: true,
            header: "Add " + schemaName,
            content: newItem.server_name + " added successfully.",
          });
          updateServers();
          handleResetScreen();
        }
      }

    } catch (e) {
      console.error(e);
      let response = '';
      if ('response' in e && 'data' in e.response) {
        //Check if errors key exists from Lambda errors.
        if (e.response.data.errors)
        {
          response = e.response.data.errors;
          response = parsePUTResponseErrors(response);
        } else if (e.response.data.cause){
          response = e.response.data.cause;
        } else {
          response = 'Unknown error occurred.';
        }
      } else {
        response = 'Unknown error occurred.';
      }

      handleNotification({
        type: 'error',
        dismissible: true,
        header: "Save " + schemaName,
        content: (response)
      });
    }
  }

  async function handleRefreshClick(e) {
    e.preventDefault();
    await updateServers();
  }

  async function handleDeleteItemClick(e) {
    e.preventDefault();
    showDeleteConfirmaton();
  }

  async function handleDeleteItem(e) {
    e.preventDefault();

    await hideDeleteConfirmaton();

    let currentItem = 0;
    let multiReturnMessage = [];
    let notificationId;

    try {
      const session = await Auth.currentSession();
      const apiUser = new User(session);
      if(selectedItems.length > 1) {
        notificationId = handleNotification({
          type: 'success',
          loading: true,
          dismissible: false,
          header: "Deleting selected servers..."
        });
      }
      for(let item in selectedItems) {
        currentItem = item;
        await apiUser.deleteServer(selectedItems[item].server_id);
        //Combine notifications into a single message if multi selected used, to save user dismiss clicks.
        if(selectedItems.length > 1){
          multiReturnMessage.push(selectedItems[item].server_name);
        } else {
          handleNotification({
            type: 'success',
            dismissible: true,
            header: 'Server deleted successfully',
            content: selectedItems[item].server_name + ' was deleted.'
          });
        }

      }

      //Create notification where multi select was used.
      if(selectedItems.length > 1){
        handleNotification({
          id: notificationId,
          type: 'success',
          dismissible: true,
          header: 'Servers deleted successfully',
          content: multiReturnMessage.join(", ") + ' were deleted.'
        });
      }


      //Unselect applications marked for deletion to clear apps.
      setSelectedItems([]);
      await updateServers();

    } catch (e) {
      console.log(e);
        handleNotification({
            type: 'error',
            dismissible: true,
            header: 'Server deletion failed',
            content: selectedItems[currentItem].server_name + ' failed to delete.'
          });
    }
  }

  function displayItemsViewScreen(){
    return <SpaceBetween direction="vertical" size="xs">
      <ItemTable
        sendNotification={handleNotification}
        schema={props.schema[schemaName]}
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
        handleDeleteItem={handleDeleteItemClick}
        handleEditItem={handleEditItem}
        handleDownloadItems={handleDownloadItems}
        userAccess={props.userEntityAccess}
        setHelpPanelContent={props.setHelpPanelContent}
      />
      <ViewServer
        schema={props.schema}
        dataAll={dataAll}
        selectedItems={selectedItems}
        isLoadingApps={isLoadingApps}
        errorApps={errorApps}
      />
    </SpaceBetween>;
  }

  function displayItemsScreen(){
    if (editingItem){
      return <ItemAmend action={action} schemaName={schemaName} schemas={props.schema} userAccess={props.userEntityAccess}  item={focusItem} handleSave={handleSave} handleCancel={handleResetScreen} updateNotification={handleNotification} setHelpPanelContent={props.setHelpPanelContent}/>
    } else {
      return displayItemsViewScreen();
    }
  }

  useEffect( () => {
    let selected = [];

    if (!isLoadingServers) {

      let item = dataServers.filter(function (entry) {
        return entry[itemIDKey] === params.id;
      });

      if (item.length === 1) {
          selected.push(item[0]);
          handleItemSelectionChange(selected);
          //Check if URL contains edit path and switch to amend component.
          if (location.pathname && location.pathname.match('/edit/')) {
            handleEditItem(item[0]);
          }
      } else if (location.pathname && location.pathname.match('/add')) {
        //Add url used, redirect to add screen.
        handleAddItem();
      }
    }

  }, [dataServers]);

  //Update help tools panel.
  useEffect(() => {
    if (props.schema) {
      let tempContent = undefined;
      if (props.schema[schemaName].help_content) {
        tempContent = props.schema[schemaName].help_content;
        tempContent.header = props.schema[schemaName].friendly_name ? props.schema[schemaName].friendly_name : capitalize(schemaName);
      }
      props.setHelpPanelContent(tempContent)
    }
  }, [props.schema]);

  return (
    <div>
      {props.schemaIsLoading ?
        <StatusIndicator type="loading">
          Loading schema...
        </StatusIndicator>
        :
        displayItemsScreen()
        }
      <DeleteModal title={'Delete servers'} onConfirmation={handleDeleteItem}>{selectedItems.length === 1 ? <p>Are you sure you wish to delete the selected server?</p> : <p>Are you sure you wish to delete the {selectedItems.length} selected servers?</p>}</DeleteModal>
    </div>
  );
};
// Component TableView is a skeleton of a Table using AWS-UI React components.
export default UserServerTable;
