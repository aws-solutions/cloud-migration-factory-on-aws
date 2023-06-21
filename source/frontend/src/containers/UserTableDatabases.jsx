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

import DatabaseView from '../components/DatabaseView.jsx';
import { useMFApps } from "../actions/ApplicationsHook";
import { useGetDatabases } from "../actions/DatabasesHook.js";
import { useGetServers } from "../actions/ServersHook.js";
import { useMFWaves } from "../actions/WavesHook.js";
import ItemTable from '../components/ItemTable.jsx';
import { useModal } from '../actions/Modal.js';
import {parsePUTResponseErrors} from "../resources/recordFunctions";

const ViewItem = (props) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState('details');
  async function handleViewerTabChange(tabSelected)
  {
    setViewerCurrentTab(tabSelected);
  }

  if (props.selectedItems.length === 1) {

    return (
      <DatabaseView {...props}
                    database={props.selectedItems[0]}
                    handleTabChange={handleViewerTabChange}
                    dataAll={props.dataAll}
                    selectedTab={viewerCurrentTab}
      />
    );
  } else {
    return (null);
  }
}

const UserDatabaseTable = (props) => {
  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();

  //Data items for viewer and table.
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }, ] = useMFApps();
  const [{ isLoading: isLoadingMain, data: dataMain, error: errorMain }, { update: updateMain }] = useGetDatabases();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }, ] = useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, ] = useMFWaves();

  const dataAll = {application: {data: dataApps, isLoading: isLoadingApps, error: errorApps}, database: {data: dataMain, isLoading: isLoadingMain, error: errorMain}, server: {data: dataServers, isLoading: isLoadingServers, error: errorServers}, wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}};

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
  const itemIDKey = 'database_id';
  const schemaName = 'database';

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
      exportTable(selectedItems, "Databases", schemaName + 's')
    } else {
      //Download all.
      exportTable(dataServers, "Databases", schemaName + 's')
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

      //TODO Need to pull in Waves or other data here.
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
        let item_id = newItem[itemIDKey];
        let item_ref = newItem[schemaName + '_name'];

        const session = await Auth.currentSession();
        const apiUser = new User(session);
        newItem = getChanges(newItem, dataMain, itemIDKey);
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
        let resultEdit = await apiUser.putItem(item_id, newItem, schemaName);

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
          return false;
        } else {
          handleNotification({
            type: 'success',
            dismissible: true,
            header: "Update " + schemaName,
            content: item_ref + " updated successfully.",
          });
          updateMain();
          handleResetScreen();

          //This is needed to ensure the item in selectItems reflects new updates
          setSelectedItems([]);
          setFocusItem({});
        }
      }
      else {

        const session = await Auth.currentSession();
        const apiUser = new User(session);
        delete newItem[schemaName + '_id'];
        let resultAdd = await apiUser.postItem(newItem, schemaName);

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
            content: newItem[schemaName + '_name'] + " added successfully.",
          });
          updateMain();
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
    await updateMain();
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
          header: "Deleting selected " + schemaName + "s..."
        });
      }

      for(let item in selectedItems) {
        currentItem = item;
        await apiUser.deleteDatabase(selectedItems[item][schemaName + '_id']);
        //Combine notifications into a single message if multi selected used, to save user dismiss clicks.
        if(selectedItems.length > 1){
          multiReturnMessage.push(selectedItems[item][schemaName + '_name']);
        } else {
          handleNotification({
            type: 'success',
            dismissible: true,
            header: schemaName + ' deleted successfully',
            content: selectedItems[item][schemaName + '_name'] + ' was deleted.'
          });
        }

      }

      //Create notification where multi select was used.
      if(selectedItems.length > 1){
        handleNotification({
          id: notificationId,
          type: 'success',
          dismissible: true,
          header: schemaName + ' deleted successfully',
          content: multiReturnMessage.join(", ") + ' were deleted.'
        });
      }


      //Unselect applications marked for deletion to clear apps.
      setSelectedItems([]);
      await updateMain();

    } catch (e) {
      console.log(e);
        handleNotification({
            type: 'error',
            dismissible: true,
            header: schemaName + ' deletion failed',
            content: selectedItems[currentItem][schemaName + '_name'] + ' failed to delete.'
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
        userAccess={props.userEntityAccess}
        setHelpPanelContent={props.setHelpPanelContent}
      />
      <ViewItem
        schema={props.schema}
        selectedItems={selectedItems}
        dataAll={dataAll}
      />
    </SpaceBetween>
  }

  function displayItemsScreen(){
    if (editingItem){
      return <ItemAmend action={action} schemaName={schemaName} schemas={props.schema} userAccess={props.userEntityAccess} item={focusItem} handleSave={handleSave} handleCancel={handleResetScreen} updateNotification={handleNotification} setHelpPanelContent={props.setHelpPanelContent}/>;
    } else {
      return displayItemsViewScreen();
    }
  }

  useEffect( () => {
    let selected = [];

    if (!isLoadingMain) {

      let item = dataMain.filter(function (entry) {
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

  }, [dataMain]);

  //Update help tools panel.
  useEffect(() => {
    if (props.schema && props.schema[schemaName].help_content) {
      let tempContent = props.schema[schemaName].help_content;
      tempContent.header = props.schema[schemaName].friendly_name ? props.schema[schemaName].friendly_name : capitalize(schemaName);
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
      <DeleteModal title={'Delete ' + schemaName + 's'} onConfirmation={handleDeleteItem}>{selectedItems.length === 1 ? <p>{'Are you sure you wish to delete the selected ' + schemaName + '?'}</p> : <p>{'Are you sure you wish to delete the {selectedItems.length} selected ' + schemaName +'?'}</p>}</DeleteModal>
    </div>
  );
};

// Component TableView is a skeleton of a Table using AWS-UI React components.
export default UserDatabaseTable;
